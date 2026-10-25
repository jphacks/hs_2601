"""ステップ 9: 写真列の保存を、リポジトリとストレージをメモリ実装にして確認する。"""
from pathlib import Path

import httpx
import pytest

from app.external.supabase.rest import SupabaseRest
from app.repositories.supabase_repo import SupabasePhotoStorage, SupabaseRoutePlanRepository, record_to_row, row_to_record
from app.schemas.exploration import Exploration
from app.schemas.route_plan import RoutePlanRecord, plan_id_for
from app.services.creator.publish import publish_plan

FIXTURE = Path(__file__).parent / "fixtures" / "route_sample.json"


class MemoryRepo:
    def __init__(self) -> None:
        self.rows: dict[str, RoutePlanRecord] = {}

    def save(self, record: RoutePlanRecord) -> RoutePlanRecord:
        self.rows[record.id] = record
        return record

    def get_by_id(self, plan_id: str) -> RoutePlanRecord | None:
        return self.rows.get(plan_id)

    def get_by_name(self, name: str) -> RoutePlanRecord | None:
        return next((r for r in self.rows.values() if r.name == name), None)


class MemoryStorage:
    def __init__(self) -> None:
        self.files: dict[str, tuple[bytes, str]] = {}

    def put(self, path: str, data: bytes, content_type: str) -> str:
        self.files[path] = (data, content_type)
        return f"https://cdn.example/{path}"


def load_with_images(tmp_path: Path) -> Exploration:
    e = Exploration.model_validate_json(FIXTURE.read_text(encoding="utf-8"))
    (tmp_path / "images").mkdir()
    (tmp_path / "images" / "000_arrow.png").write_bytes(b"arrow0")
    (tmp_path / "images" / "001.jpg").write_bytes(b"plain1")
    p0 = e.points[0].model_copy(update={"image": "images/000.jpg", "arrow_image": "images/000_arrow.png"})
    p1 = e.points[1].model_copy(update={"image": "images/001.jpg", "arrow_image": None})
    return e.model_copy(update={"points": [p0, p1]})


def test_命名からIDが決まり_同名なら同じID() -> None:
    assert plan_id_for("四天王寺→てんしば") == plan_id_for(" 四天王寺→てんしば ")
    assert plan_id_for("a") != plan_id_for("b")
    assert len(plan_id_for("a")) == 12


def test_矢印画像を優先して上げ_画像URL入りの写真列を保存する(tmp_path: Path) -> None:
    repo, storage = MemoryRepo(), MemoryStorage()
    e = load_with_images(tmp_path)
    res = publish_plan(e, tmp_path, "テスト経路", repo, storage)

    pid = plan_id_for("テスト経路")
    assert res.record.id == pid and res.uploaded == [0, 1] and res.skipped == []
    assert storage.files[f"{pid}/000.png"] == (b"arrow0", "image/png")  # 矢印入りを優先（PNG のまま）
    assert storage.files[f"{pid}/001.jpg"] == (b"plain1", "image/jpeg")  # 無ければ採用画像
    saved = repo.get_by_name("テスト経路")
    assert saved is not None and saved.status == "published"
    assert [s.image_url for s in saved.plan.steps] == [f"https://cdn.example/{pid}/000.png", f"https://cdn.example/{pid}/001.jpg"]
    assert saved.plan.steps[0].turn == e.points[0].turn and saved.plan.polyline == e.polyline


def test_画像が無い地点はURLをnullにして続行する(tmp_path: Path) -> None:
    e = load_with_images(tmp_path)
    e = e.model_copy(update={"points": [e.points[0], e.points[1].model_copy(update={"image": None})]})
    res = publish_plan(e, tmp_path, "欠け", MemoryRepo(), MemoryStorage())
    assert res.uploaded == [0] and res.skipped == [1]
    assert res.record.plan.steps[1].image_url is None


def test_空の命名はエラー(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="命名"):
        publish_plan(load_with_images(tmp_path), tmp_path, "  ", MemoryRepo(), MemoryStorage())


def test_元のExplorationは変更されない(tmp_path: Path) -> None:
    e = load_with_images(tmp_path)
    before = e.model_dump_json()
    publish_plan(e, tmp_path, "不変", MemoryRepo(), MemoryStorage())
    assert e.model_dump_json() == before


def test_行とレコードを往復できる(tmp_path: Path) -> None:
    res = publish_plan(load_with_images(tmp_path), tmp_path, "往復", MemoryRepo(), MemoryStorage())
    row = record_to_row(res.record)
    assert row["plan_json"]["steps"][0]["image_url"].startswith("https://")
    assert row_to_record(row) == res.record


def test_Supabaseリポジトリは行を上書き保存して取り出せる(tmp_path: Path) -> None:
    table: dict[str, dict] = {}

    def handler(req: httpx.Request) -> httpx.Response:
        if req.url.path.startswith("/storage/"):
            return httpx.Response(200, json={"Key": "x"})
        if req.method == "POST":
            import json
            for row in json.loads(req.content):
                table[row["id"]] = row
            return httpx.Response(201, json=list(table.values()))
        key, val = next((k, v) for k, v in req.url.params.items() if k != "select")
        return httpx.Response(200, json=[r for r in table.values() if r[key] == val.removeprefix("eq.")])

    rest = SupabaseRest("https://p.supabase.co", "k", http=httpx.Client(transport=httpx.MockTransport(handler)))
    repo, storage = SupabaseRoutePlanRepository(rest), SupabasePhotoStorage(rest)
    e = load_with_images(tmp_path)
    first = publish_plan(e, tmp_path, "上書き", repo, storage).record
    second = publish_plan(e.model_copy(update={"total_distance_m": 999}), tmp_path, "上書き", repo, storage).record
    assert first.id == second.id and len(table) == 1
    assert repo.get_by_id(first.id) == second and repo.get_by_name("上書き") == second
    assert repo.get_by_id("nope") is None


def test_出力ディレクトリの外を指す画像パスは拒否する(tmp_path: Path) -> None:
    e = load_with_images(tmp_path)
    (tmp_path.parent / "secret.jpg").write_bytes(b"x")
    bad = e.model_copy(update={"points": [e.points[0].model_copy(update={"arrow_image": "../secret.jpg"})]})
    with pytest.raises(ValueError, match="外"):
        publish_plan(bad, tmp_path, "逸脱", MemoryRepo(), MemoryStorage())


def test_不正なIDは拒否する(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="公開 ID"):
        publish_plan(load_with_images(tmp_path), tmp_path, "x", MemoryRepo(), MemoryStorage(), plan_id="a/../b")


def test_同じ命名が別IDで存在すれば画像を上げる前に止める(tmp_path: Path) -> None:
    repo, storage = MemoryRepo(), MemoryStorage()
    e = load_with_images(tmp_path)
    publish_plan(e, tmp_path, "重複", repo, storage)
    n = len(storage.files)
    with pytest.raises(ValueError, match="既に"):
        publish_plan(e, tmp_path, "重複", repo, storage, plan_id="other1")
    assert len(storage.files) == n

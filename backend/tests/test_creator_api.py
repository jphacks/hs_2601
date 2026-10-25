"""作る人の HTTP API（docs/interface.md 5 章）。Supabase・パイプラインはメモリ実装に差し替える（ネットワークなし）。"""
from __future__ import annotations

import json
from io import BytesIO
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from app.api.deps import (
    get_admin_repo, get_job_store, get_photo_storage, get_pipeline_runner, get_public_base_url, get_work_root,
)
from app.imaging.qr import read_qr
from app.main import app
from app.schemas.creator_input import PlanInput
from app.schemas.exploration import Exploration
from app.schemas.route_plan import PlanStatus, RoutePlanRecord, RoutePlanSummary, plan_id_for
from app.services.creator.jobs import JobStore
from app.services.creator.pipeline import PipelineResult, Reporter
from tests.test_publish import MemoryStorage

FIXTURE = Path(__file__).parent / "fixtures" / "route_sample.json"
BASE_URL = "https://walk.example"
NAME = "四天王寺→てんしば"
RID = plan_id_for(NAME)


class MemoryRepo:
    def __init__(self) -> None:
        self.rows: dict[str, RoutePlanRecord] = {}
        self.created: dict[str, str] = {}
        self._clock = 0

    def save(self, record: RoutePlanRecord) -> RoutePlanRecord:
        self._clock += 1
        self.created.setdefault(record.id, f"2026-10-25T10:00:{self._clock:02d}+00:00")
        self.rows[record.id] = record
        return record

    def get_by_id(self, plan_id: str) -> RoutePlanRecord | None:
        return self.rows.get(plan_id)

    def get_by_name(self, name: str) -> RoutePlanRecord | None:
        return next((r for r in self.rows.values() if r.name == name), None)

    def list_by_creator(self, creator_id: str) -> list[RoutePlanSummary]:
        rows = [RoutePlanSummary(**r.model_dump(include={"id", "name", "status", "origin", "destination"}), created_at=self.created[r.id])
                for r in self.rows.values() if r.creator_id == creator_id]
        return sorted(rows, key=lambda s: s.created_at or "", reverse=True)

    def set_status(self, plan_id: str, status: PlanStatus) -> RoutePlanRecord | None:
        rec = self.rows.get(plan_id)
        if rec is None:
            return None
        self.rows[plan_id] = rec.model_copy(update={"status": status})
        return self.rows[plan_id]

    def update_draft_plan(self, plan_id: str, plan) -> RoutePlanRecord | None:  # noqa: ANN001
        rec = self.rows.get(plan_id)
        if rec is None or rec.status != "draft":
            return None
        self.rows[plan_id] = rec.model_copy(update={"plan": plan})
        return self.rows[plan_id]


class FakePipeline:
    """fixture の Exploration を返す。最初の地点の画像を 1 枚目の写真にして、保存（画像アップロード）まで通す。"""

    def __init__(self, fail: Exception | None = None) -> None:
        self.fail = fail
        self.calls: list[tuple[PlanInput, Path]] = []

    def run(self, plan: PlanInput, work_dir: Path, rep: Reporter = Reporter()) -> PipelineResult:
        self.calls.append((plan, work_dir))
        for step in ("geocode", "route", "streetview", "landmark", "arrow"):
            rep.on_step(step)
            if self.fail and step == "route":
                raise self.fail
        e = Exploration.model_validate_json(FIXTURE.read_text(encoding="utf-8"))
        image = plan.photos[0].image if plan.photos else None
        points = [e.points[0].model_copy(update={"image": image}), *e.points[1:]]
        e = e.model_copy(update={"points": points})
        return PipelineResult(e, e.origin, e.destination)


def jpeg(color: str = "red", size: tuple[int, int] = (2000, 1000)) -> bytes:
    buf = BytesIO()
    Image.new("RGB", size, color).save(buf, format="JPEG")
    return buf.getvalue()


def manifest(n_photos: int = 2, *, name: str = NAME, creator_id: str | None = "c_me") -> dict:
    photos = [{"id": f"p{i}", "seq": i, "image": f"photos/p{i}.jpg", "lat": 34.65 + i * 0.001, "lng": 135.51} for i in range(n_photos)]
    return {"version": 1, "name": name, "origin": "四天王寺 南大門",
            "destination": {"query": "現在地", "lat": 34.6485, "lng": 135.5110}, "creator_id": creator_id, "photos": photos}


def files_for(m: dict) -> list[tuple[str, tuple[str, bytes, str]]]:
    return [("photos", (f"{p['id']}.jpg", jpeg(), "image/jpeg")) for p in m["photos"]]


class Ctx:
    def __init__(self, tmp_path: Path) -> None:
        self.repo = MemoryRepo()
        self.storage = MemoryStorage()
        self.pipeline = FakePipeline()
        self.store = JobStore()
        self.work_root = tmp_path / "routes"
        app.dependency_overrides.update({
            get_admin_repo: lambda: self.repo, get_photo_storage: lambda: self.storage,
            get_pipeline_runner: lambda: self.pipeline, get_job_store: lambda: self.store,
            get_work_root: lambda: self.work_root, get_public_base_url: lambda: BASE_URL,
        })
        self.client = TestClient(app)

    def post(self, m: dict | str | None, files=None):
        data = {} if m is None else {"manifest": m if isinstance(m, str) else json.dumps(m, ensure_ascii=False)}
        if files is None and isinstance(m, dict):
            files = files_for(m)
        return self.client.post("/api/routes", data=data, files=files or None)


@pytest.fixture
def ctx(tmp_path: Path) -> Ctx:
    c = Ctx(tmp_path)
    yield c
    app.dependency_overrides.clear()


# --- 作成受付 ---

def test_作成から公開までの一連の流れ(ctx: Ctx) -> None:
    res = ctx.post(manifest())
    assert res.status_code == 202, res.text
    body = res.json()
    assert set(body) == {"jobId", "routeId"} and body["routeId"] == RID

    job = ctx.client.get(f"/api/jobs/{body['jobId']}").json()
    assert job == {"jobId": body["jobId"], "state": "done", "step": "save", "routeId": RID, "message": None}

    # 作業ディレクトリ: 正規化した写真と photos.json
    plan, work_dir = ctx.pipeline.calls[0]
    assert work_dir == ctx.work_root / RID and plan.creator_id == "c_me"
    assert Image.open(work_dir / "photos" / "p0.jpg").size == (1280, 640)
    assert PlanInput.model_validate_json((work_dir / "photos.json").read_text(encoding="utf-8")).name == NAME

    # 下書きで保存され、作成者 ID が付く
    rec = ctx.repo.rows[RID]
    assert rec.status == "draft" and rec.creator_id == "c_me" and rec.name == NAME
    assert rec.plan.steps[0].image_url == f"https://cdn.example/{RID}/000.jpg"

    listed = ctx.client.get("/api/routes", params={"creator_id": "c_me"}).json()
    assert listed == [{"id": RID, "name": NAME, "origin": rec.origin, "destination": rec.destination, "status": "draft",
                       "createdAt": ctx.repo.created[RID]}]

    detail = ctx.client.get(f"/api/routes/{RID}").json()
    assert detail["status"] == "draft" and detail["creator_id"] == "c_me" and "distance_to_next_m" in detail["plan"]["steps"][0]

    pub = ctx.client.post(f"/api/routes/{RID}/publish")
    assert pub.status_code == 200
    assert pub.json() == {"routeId": RID, "url": f"{BASE_URL}/r/{RID}", "qrPath": f"/api/routes/{RID}/qr.png"}
    assert ctx.repo.rows[RID].status == "published"
    assert ctx.client.post(f"/api/routes/{RID}/publish").json() == pub.json()  # 2 回目も同じ

    qr = ctx.client.get(pub.json()["qrPath"])
    assert qr.status_code == 200 and qr.headers["content-type"] == "image/png"
    assert read_qr(qr.content) == f"{BASE_URL}/r/{RID}"


def test_写真0枚でも受け付ける(ctx: Ctx) -> None:
    # フロントの FormData と同じく、manifest だけの multipart で送る
    boundary = "xBOUNDARYx"
    body = (f"--{boundary}\r\nContent-Disposition: form-data; name=\"manifest\"\r\n\r\n"
            f"{json.dumps(manifest(0), ensure_ascii=False)}\r\n--{boundary}--\r\n").encode("utf-8")
    res = ctx.client.post("/api/routes", content=body, headers={"content-type": f"multipart/form-data; boundary={boundary}"})
    assert res.status_code == 202, res.text
    assert ctx.client.get(f"/api/jobs/{res.json()['jobId']}").json()["state"] == "done"
    assert ctx.repo.rows[RID].plan.steps[0].image_url is None


def test_目的地を省略しても受け付ける_写真も無ければ400(ctx: Ctx) -> None:
    m = {k: v for k, v in manifest(2).items() if k != "destination"}
    res = ctx.client.post("/api/routes", data={"manifest": json.dumps(m, ensure_ascii=False)}, files=files_for(m))
    assert res.status_code == 202, res.text
    empty = {**m, "photos": []}
    res = ctx.client.post("/api/routes", data={"manifest": json.dumps(empty, ensure_ascii=False)})
    assert res.status_code == 400 and "写真が 1 枚以上" in res.json()["detail"]


def test_同じ作成者なら上書きでき_別の作成者なら409(ctx: Ctx) -> None:
    assert ctx.post(manifest()).status_code == 202
    assert ctx.post(manifest(1)).status_code == 202
    assert len(ctx.pipeline.calls) == 2 and not (ctx.work_root / RID / "photos" / "p1.jpg").exists()  # 前回の写真は消える

    res = ctx.post(manifest(creator_id="c_other"))
    assert res.status_code == 409 and "detail" in res.json()
    assert ctx.repo.rows[RID].creator_id == "c_me" and len(ctx.pipeline.calls) == 2


def test_作成中の同じ道案内は409(ctx: Ctx) -> None:
    assert ctx.store.start(RID) is not None
    assert ctx.post(manifest()).status_code == 409


@pytest.mark.parametrize("m", [None, "", "{not json", json.dumps({"name": "x"}),
                               json.dumps(manifest(creator_id=None)), json.dumps(manifest(creator_id="  ")),
                               json.dumps({**manifest(), "photos": [{**manifest()["photos"][0], "seq": 1}]})])
def test_manifestが不正なら400(ctx: Ctx, m: str | None) -> None:
    res = ctx.post(m, files=files_for(manifest()) if m else None)
    assert res.status_code == 400, res.text
    assert isinstance(res.json()["detail"], str) and ctx.pipeline.calls == []


def test_写真ファイルの過不足は400(ctx: Ctx) -> None:
    m = manifest(2)
    missing = ctx.post(m, files=files_for(m)[:1])
    assert missing.status_code == 400 and "p1.jpg" in missing.json()["detail"]
    extra = ctx.post(m, files=[*files_for(m), ("photos", ("zz.jpg", jpeg(), "image/jpeg"))])
    assert extra.status_code == 400 and "zz.jpg" in extra.json()["detail"]
    dup = ctx.post(m, files=[*files_for(m), files_for(m)[0]])
    assert dup.status_code == 400
    assert ctx.pipeline.calls == [] and ctx.store.start(RID) is not None  # ジョブも作られていない


def test_画像として開けない写真は400(ctx: Ctx) -> None:
    m = manifest(1)
    res = ctx.post(m, files=[("photos", ("p0.jpg", b"HEIC?not-an-image", "image/heic"))])
    assert res.status_code == 400 and "p0.jpg" in res.json()["detail"]
    assert not (ctx.work_root / RID).exists()


# --- ジョブ ---

def test_失敗したジョブは利用者向けの文を返す(ctx: Ctx) -> None:
    ctx.pipeline.fail = ValueError("経路が取れた区間がありません")
    job_id = ctx.post(manifest()).json()["jobId"]
    job = ctx.client.get(f"/api/jobs/{job_id}").json()
    assert job["state"] == "failed" and job["step"] == "route" and "経路が見つかりませんでした" in job["message"]
    assert RID not in ctx.repo.rows
    assert ctx.post(manifest()).status_code == 202  # 失敗後は作り直せる


def test_無いジョブは404(ctx: Ctx) -> None:
    assert ctx.client.get("/api/jobs/nope").status_code == 404


# --- 一覧・詳細・公開・QR ---

def test_一覧はcreator_idが無ければ400_他人の道は出ない(ctx: Ctx) -> None:
    assert ctx.client.get("/api/routes").status_code == 400
    assert ctx.client.get("/api/routes", params={"creator_id": ""}).status_code == 400
    ctx.post(manifest())
    ctx.post(manifest(name="二本目"))
    ctx.post(manifest(name="他人の道", creator_id="c_other"))
    ids = [r["id"] for r in ctx.client.get("/api/routes", params={"creator_id": "c_me"}).json()]
    assert ids == [plan_id_for("二本目"), RID]  # 新しい順


@pytest.mark.parametrize("path", ["/api/routes/{id}", "/api/routes/{id}/qr.png"])
def test_無いIDと不正なIDは404(ctx: Ctx, path: str) -> None:
    assert ctx.client.get(path.format(id="abcdef123456")).status_code == 404
    assert ctx.client.get(path.format(id="a%20b")).status_code == 404


def test_無い道案内の公開は404(ctx: Ctx) -> None:
    assert ctx.client.post("/api/routes/abcdef123456/publish").status_code == 404


# --- 公開中の道案内を守る ---

def test_公開中の道案内は同じ作成者でも作り直せない_作業ディレクトリも消さない(ctx: Ctx) -> None:
    assert ctx.post(manifest()).status_code == 202
    assert ctx.client.post(f"/api/routes/{RID}/publish").status_code == 200
    published = ctx.repo.rows[RID]
    kept = ctx.work_root / RID / "photos" / "p1.jpg"
    assert kept.exists()

    res = ctx.post(manifest(1))
    assert res.status_code == 409 and "公開中" in res.json()["detail"]
    assert ctx.repo.rows[RID] == published and len(ctx.pipeline.calls) == 1  # 保存もパイプラインも走らない
    assert kept.exists()  # 前回の作業ディレクトリもそのまま


# --- 写真列から写真を外す ---

def _draft_with_steps(ctx: Ctx, distances: list[int]) -> None:
    assert ctx.post(manifest()).status_code == 202
    rec = ctx.repo.rows[RID]
    base = rec.plan.steps[0]
    turns = ["straight"] + ["left"] * (len(distances) - 2) + ["arrive"]
    steps = [base.model_copy(update={"index": i, "turn": t, "distance_to_next_m": d, "image_url": f"https://cdn/{i}.png"})
             for i, (t, d) in enumerate(zip(turns, distances))]
    ctx.repo.rows[RID] = rec.model_copy(update={"plan": rec.plan.model_copy(update={"steps": steps})})


def _remove(ctx: Ctx, indices: list[int], creator_id: str = "c_me"):
    return ctx.client.post(f"/api/routes/{RID}/steps/remove", json={"creatorId": creator_id, "indices": indices})


def test_下書きの写真を選んで外すと_距離は直前の地点に足される(ctx: Ctx) -> None:
    _draft_with_steps(ctx, [100, 20, 30, 50, 0])
    res = _remove(ctx, [1, 2])
    assert res.status_code == 200, res.text
    steps = res.json()["plan"]["steps"]
    assert [s["image_url"] for s in steps] == ["https://cdn/0.png", "https://cdn/3.png", "https://cdn/4.png"]
    assert [s["distance_to_next_m"] for s in steps] == [150, 50, 0] and [s["index"] for s in steps] == [0, 1, 2]
    assert ctx.repo.rows[RID].status == "draft" and len(ctx.repo.rows[RID].plan.steps) == 3


def test_ゴールは外せず_範囲外や空は400(ctx: Ctx) -> None:
    _draft_with_steps(ctx, [100, 20, 0])
    assert _remove(ctx, [2]).status_code == 400
    assert _remove(ctx, [5]).status_code == 400
    assert _remove(ctx, []).status_code == 422
    assert len(ctx.repo.rows[RID].plan.steps) == 3


def test_公開中の道案内からは外せない(ctx: Ctx) -> None:
    _draft_with_steps(ctx, [100, 20, 0])
    assert ctx.client.post(f"/api/routes/{RID}/publish").status_code == 200
    before = ctx.repo.rows[RID]
    res = _remove(ctx, [1])
    assert res.status_code == 409 and ctx.repo.rows[RID] == before


def test_他の作成者は外せない(ctx: Ctx) -> None:
    _draft_with_steps(ctx, [100, 20, 0])
    assert _remove(ctx, [1], creator_id="c_other").status_code == 403
    assert len(ctx.repo.rows[RID].plan.steps) == 3

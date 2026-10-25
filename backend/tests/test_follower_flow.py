"""参加者の流れをバックエンド内だけで通す: 保存 → QR → 読み取り → URL → id → anon で取得 → 表示。

Supabase は HTTP モック。実物を叩く版は test_live_* （`pytest -m live`）。
"""
import json
import os
from pathlib import Path

import httpx
import pytest

from app.core.config import Settings
from app.external.supabase.rest import SupabaseRest
from app.imaging.qr import read_qr
from app.repositories.supabase_repo import SupabasePhotoStorage, SupabaseRoutePlanRepository
from app.schemas.exploration import Exploration
from app.schemas.route_plan import plan_id_for
from app.services.creator.publish import publish_plan
from app.services.creator.qr import write_qr
from app.services.follower.fetch import fetch_plan, plan_id_from_url
from app.services.follower.view import render_plan_html

FIXTURE = Path(__file__).parent / "fixtures" / "route_sample.json"
BASE_URL = "https://example.vercel.app"
SUPABASE = "https://proj.supabase.co"


class FakeSupabase:
    """PostgREST と Storage の最小限の振る舞い。anon キーには published の行しか見せない。"""

    def __init__(self) -> None:
        self.rows: dict[str, dict] = {}
        self.objects: dict[str, bytes] = {}

    def handler(self, req: httpx.Request) -> httpx.Response:
        key = req.headers.get("apikey")
        if req.url.path.startswith("/storage/v1/object/public/"):
            data = self.objects.get(req.url.path.removeprefix("/storage/v1/object/public/"))
            return httpx.Response(200, content=data, headers={"content-type": "image/jpeg"}) if data else httpx.Response(404)
        if req.url.path.startswith("/storage/v1/object/"):
            assert key == "service"
            self.objects[req.url.path.removeprefix("/storage/v1/object/")] = req.content
            return httpx.Response(200, json={})
        assert req.url.path == "/rest/v1/route_plans"
        if req.method == "POST":
            assert key == "service"
            for row in json.loads(req.content):
                self.rows[row["id"]] = row
            return httpx.Response(201, json=list(self.rows.values()))
        rows = list(self.rows.values())
        if key == "anon":
            rows = [r for r in rows if r["status"] == "published"]  # RLS
        for k, v in req.url.params.items():
            if k != "select":
                rows = [r for r in rows if r[k] == v.removeprefix("eq.")]
        return httpx.Response(200, json=rows)


def prepared(tmp_path: Path) -> Exploration:
    e = Exploration.model_validate_json(FIXTURE.read_text(encoding="utf-8"))
    (tmp_path / "images").mkdir()
    pts = []
    for p in e.points:
        (tmp_path / "images" / f"{p.index:03d}_arrow.jpg").write_bytes(b"\xff\xd8arrow%d" % p.index)
        pts.append(p.model_copy(update={"image": f"images/{p.index:03d}.jpg", "arrow_image": f"images/{p.index:03d}_arrow.jpg"}))
    return e.model_copy(update={"points": pts})


def test_QRを読んで写真列を取得し表示できる(tmp_path: Path) -> None:
    fake = FakeSupabase()
    http = httpx.Client(transport=httpx.MockTransport(fake.handler))

    # 作る人側: service_role で保存し、QR を出す
    service = SupabaseRest(SUPABASE, "service", http=http)
    rec = publish_plan(prepared(tmp_path), tmp_path, "テスト経路", SupabaseRoutePlanRepository(service), SupabasePhotoStorage(service)).record
    qr = write_qr(tmp_path, BASE_URL, rec.id)
    assert qr.path.name == "qr.png" and qr.url == f"{BASE_URL}/r/{plan_id_for('テスト経路')}"

    # 参加者側: スマホのカメラの代わりに QR を読む → URL → id → anon キーで取得
    url = read_qr(qr.path.read_bytes())
    assert url == qr.url
    anon = SupabaseRest(SUPABASE, "anon", http=http)
    got = fetch_plan(SupabaseRoutePlanRepository(anon), plan_id_from_url(url))
    assert got is not None and got == rec
    assert [s.image_url for s in got.plan.steps] == [f"{SUPABASE}/storage/v1/object/public/plans/{rec.id}/{i:03d}.jpg" for i in range(len(rec.plan.steps))]

    # 表示: 画像 URL が <img> に入り、画像そのものも認証なしで取れる
    page = render_plan_html(got)
    for s in got.plan.steps:
        assert f'<img src="{s.image_url}"' in page
        assert http.get(s.image_url).content == b"\xff\xd8arrow%d" % s.index
    assert got.plan.steps[0].landmark or "" in page


def test_未公開の行はanonでは見えない(tmp_path: Path) -> None:
    fake = FakeSupabase()
    http = httpx.Client(transport=httpx.MockTransport(fake.handler))
    service = SupabaseRest(SUPABASE, "service", http=http)
    rec = publish_plan(prepared(tmp_path), tmp_path, "下書き", SupabaseRoutePlanRepository(service), SupabasePhotoStorage(service)).record
    fake.rows[rec.id]["status"] = "draft"
    anon = SupabaseRoutePlanRepository(SupabaseRest(SUPABASE, "anon", http=http))
    assert fetch_plan(anon, rec.id) is None


def test_存在しないIDはNone() -> None:
    http = httpx.Client(transport=httpx.MockTransport(FakeSupabase().handler))
    assert fetch_plan(SupabaseRoutePlanRepository(SupabaseRest(SUPABASE, "anon", http=http)), "nope") is None


@pytest.mark.live
def test_live_実際のSupabaseからQR経由で写真列と画像が取れる(tmp_path: Path) -> None:
    """前提: 事前に `scripts.publish --name "四天王寺→てんしば"` 済み。`pytest -m live` で実行。"""
    s = Settings()
    if not (s.supabase_url and s.supabase_anon_key and s.public_base_url):
        pytest.skip("SUPABASE_URL / SUPABASE_ANON_KEY / PUBLIC_BASE_URL が無い")
    name = os.environ.get("LIVE_PLAN_NAME", "四天王寺→てんしば")
    qr = write_qr(tmp_path, s.public_base_url, plan_id_for(name))
    url = read_qr(qr.path.read_bytes())
    assert url is not None
    repo = SupabaseRoutePlanRepository(SupabaseRest(s.supabase_url, s.supabase_anon_key))
    rec = fetch_plan(repo, plan_id_from_url(url))
    assert rec is not None and rec.name == name and rec.status == "published"
    assert len(rec.plan.steps) >= 2 and all(st.image_url for st in rec.plan.steps)
    res = httpx.get(rec.plan.steps[0].image_url, timeout=30)
    assert res.status_code == 200 and res.headers["content-type"].startswith("image/")
    assert "<img" in render_plan_html(rec)

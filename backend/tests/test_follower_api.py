"""GET /r/{id} と GET /api/public/routes/{id}。Supabase はメモリ実装に差し替える。"""
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.api.deps import get_public_repo
from app.main import app
from app.schemas.route_plan import RoutePlan, RoutePlanRecord, RouteStep

FIXTURE = Path(__file__).parent / "fixtures" / "route_sample.json"


def record() -> RoutePlanRecord:
    steps = [RouteStep(index=0, lat=34.7, lng=135.5, turn="straight", instruction="直進", landmark="赤い看板", distance_to_next_m=50,
                       image_url="https://cdn.example/plans/abc/000.jpg"),
             RouteStep(index=1, lat=34.7, lng=135.5, turn="arrive", instruction="到着", landmark=None, distance_to_next_m=0, image_url=None)]
    plan = RoutePlan(origin="A", destination="B", polyline="xyz", total_distance_m=50, steps=steps)
    return RoutePlanRecord(id="abc123", name="テスト", origin="A", destination="B", plan=plan)


class MemoryRepo:
    def __init__(self, *recs: RoutePlanRecord) -> None:
        self.rows = {r.id: r for r in recs}

    def save(self, r: RoutePlanRecord) -> RoutePlanRecord:
        self.rows[r.id] = r
        return r

    def get_by_id(self, plan_id: str) -> RoutePlanRecord | None:
        return self.rows.get(plan_id)

    def get_by_name(self, name: str) -> RoutePlanRecord | None:
        return next((r for r in self.rows.values() if r.name == name), None)


@pytest.fixture
def client() -> TestClient:
    app.dependency_overrides[get_public_repo] = lambda: MemoryRepo(record())
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_参加者ページは画像入りHTMLを返す(client: TestClient) -> None:
    res = client.get("/r/abc123")
    assert res.status_code == 200 and res.headers["content-type"].startswith("text/html")
    assert '<img src="https://cdn.example/plans/abc/000.jpg"' in res.text
    assert "赤い看板" in res.text and "画像なし" in res.text


def test_公開JSONは契約の形で返す(client: TestClient) -> None:
    body = client.get("/api/public/routes/abc123").json()
    assert body["id"] == "abc123" and body["status"] == "published"
    assert body["plan"]["steps"][0]["image_url"].startswith("https://") and body["plan"]["steps"][1]["image_url"] is None


def test_無いIDは404(client: TestClient) -> None:
    assert client.get("/r/zzz").status_code == 404
    assert client.get("/api/public/routes/zzz").status_code == 404


def test_不正なIDは404で_取得に行かない(client: TestClient) -> None:
    assert client.get("/r/a%2F..%2Fb").status_code == 404

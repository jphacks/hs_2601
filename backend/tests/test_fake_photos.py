"""手順 11: 実レスポンス（routes_sample.json）から、Street View をモックして photos.json を作る。"""
import json
from pathlib import Path

import httpx

from app.external.google.street_view import StreetViewClient
from app.schemas.exploration import Place
from app.services.creator.fake_photos import make_fake_photos, pick_shoot_points
from app.services.creator.photos import load_plan_input
from app.services.creator.route import route_from_raw

FIX = Path(__file__).parent / "fixtures"
ROUTE = route_from_raw(json.loads((FIX / "routes_sample.json").read_text(encoding="utf-8"))).route
ORIGIN, DEST = Place(query="大阪駅", lat=34.7025, lng=135.4959), Place(query="グランフロント大阪", lat=34.7049, lng=135.4945)
JPEG = b"\xff\xd8\xff\xe0fake"


def sv_client() -> StreetViewClient:
    def handler(req: httpx.Request) -> httpx.Response:
        if req.url.path.endswith("/metadata"):
            lat, lng = map(float, req.url.params["location"].split(","))
            return httpx.Response(200, json={"status": "OK", "pano_id": f"P{lat:.4f}", "date": "2024-01", "copyright": "© 2026 Google",
                                             "location": {"lat": lat + 0.00005, "lng": lng}})
        return httpx.Response(200, content=JPEG, headers={"content-type": "image/jpeg"})
    return StreetViewClient("k", http=httpx.Client(transport=httpx.MockTransport(handler)))


def test_曲がり角から等間隔に選び_足りなければ弧長で補う() -> None:
    pts = pick_shoot_points(ROUTE, ORIGIN, DEST, 2)
    assert len(pts) == 2 and all(p.maneuver not in ("DEPART", "ARRIVE") for p in pts)
    many = pick_shoot_points(ROUTE, ORIGIN, DEST, 50)
    assert len(many) == 50 and any(p.maneuver == "ARC" for p in many)


def test_photos_jsonと写真ができ_検証を通る(tmp_path: Path) -> None:
    plan, stats = make_fake_photos(sv_client(), ROUTE, ORIGIN, DEST, 3, tmp_path, "テスト")
    assert len(plan.photos) == 3 and stats.missing == []
    assert [p.seq for p in plan.photos] == [0, 1, 2] and [p.image for p in plan.photos] == ["photos/sv0.jpg", "photos/sv1.jpg", "photos/sv2.jpg"]
    assert plan.origin.lat == ORIGIN.lat and plan.photos[0].accuracy_m == 10
    assert (tmp_path / "photos" / "sv0.jpg").read_bytes() == JPEG
    reloaded = load_plan_input(tmp_path)  # 手順 1・2 の検証を通る
    assert reloaded == plan

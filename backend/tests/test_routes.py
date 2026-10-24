"""Routes API クライアントを、HTTP をモックして確認する（API キー不要）。"""
import json
from pathlib import Path

import httpx
import pytest

from app.external.google.routes import LatLng, RoutesClient, RoutesError, build_request_body, parse_routes_response
from app.schemas.exploration import Place
from app.services.creator.route import compute_route, decode_polyline, route_from_raw

FIXTURE = json.loads((Path(__file__).parent / "fixtures" / "routes_sample.json").read_text(encoding="utf-8"))
OSAKA = LatLng(34.7024854, 135.4959506)
GFO = LatLng(34.7039162, 135.4940095)


def test_リクエストは徒歩_日本語_メートル() -> None:
    body = build_request_body(OSAKA, GFO, [], optimize=True)
    assert body["travelMode"] == "WALK"
    assert body["languageCode"] == "ja"
    assert body["origin"]["location"]["latLng"]["latitude"] == OSAKA.lat
    assert "intermediates" not in body


def test_経由地が2つ以上なら順序最適化() -> None:
    body = build_request_body(OSAKA, GFO, [OSAKA, GFO], optimize=True)
    assert len(body["intermediates"]) == 2
    assert body["optimizeWaypointOrder"] is True
    body1 = build_request_body(OSAKA, GFO, [OSAKA], optimize=True)
    assert "optimizeWaypointOrder" not in body1  # 1 つなら最適化不要


def test_キーはヘッダーで渡し_POST_する() -> None:
    def handler(req: httpx.Request) -> httpx.Response:
        assert req.method == "POST"
        assert req.headers["X-Goog-Api-Key"] == "dummy-key"
        assert "routes.polyline.encodedPolyline" in req.headers["X-Goog-FieldMask"]
        return httpx.Response(200, json=FIXTURE)

    client = RoutesClient("dummy-key", http=httpx.Client(transport=httpx.MockTransport(handler)))
    route = client.compute_walking_route(OSAKA, GFO)
    assert route.distance_m > 0
    assert len(route.steps) > 0


def test_生レスポンスを解釈できる() -> None:
    route = parse_routes_response(FIXTURE)
    assert route.distance_m == 383
    assert route.duration_s > 0
    assert route.polyline
    assert len(route.steps) == 8
    turns = [s.maneuver for s in route.steps if s.maneuver.startswith("TURN")]
    assert turns == ["TURN_LEFT", "TURN_RIGHT"]
    assert all(s.distance_m >= 0 for s in route.steps)


def test_経路0件はエラー() -> None:
    with pytest.raises(RoutesError):
        parse_routes_response({"routes": []})


def test_HTTPエラーはメッセージ付きで伝わる() -> None:
    def handler(req: httpx.Request) -> httpx.Response:
        return httpx.Response(403, json={"error": {"message": "Routes API has not been used in project"}})

    client = RoutesClient("dummy-key", http=httpx.Client(transport=httpx.MockTransport(handler)))
    with pytest.raises(RoutesError, match="403.*not been used"):
        client.compute_walking_route(OSAKA, GFO)


def test_service_は_Place_で呼べる() -> None:
    def handler(req: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=FIXTURE)

    client = RoutesClient("dummy-key", http=httpx.Client(transport=httpx.MockTransport(handler)))
    out = compute_route(client, Place(query="大阪駅", lat=OSAKA.lat, lng=OSAKA.lng), Place(query="GFO", lat=GFO.lat, lng=GFO.lng))
    assert out.route.distance_m == 383
    assert route_from_raw(out.raw).route.distance_m == 383


def test_ポリラインを座標列に戻せる() -> None:
    route = parse_routes_response(FIXTURE)
    pts = decode_polyline(route.polyline)
    assert len(pts) >= 2
    # 先頭は出発地、末尾は目的地の近く（数十 m 以内）
    assert abs(pts[0][0] - OSAKA.lat) < 0.001 and abs(pts[0][1] - OSAKA.lng) < 0.001
    assert abs(pts[-1][0] - GFO.lat) < 0.001 and abs(pts[-1][1] - GFO.lng) < 0.001
    assert decode_polyline("") == []

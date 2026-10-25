"""Street View クライアントとサービスを、HTTP をモックして確認する（API キー不要）。"""
import json
from pathlib import Path

import httpx
import pytest

from app.external.google.street_view import StreetViewClient, StreetViewError, parse_metadata
from app.schemas.exploration import Exploration
from app.services.creator.streetview import StreetViewOptions, camera_heading, fetch_images

FIXTURE = Path(__file__).parent / "fixtures" / "route_sample.json"
JPEG = b"\xff\xd8\xff\xe0fakejpeg"


def make_client(has_image: bool = True, deny: bool = False) -> StreetViewClient:
    def handler(req: httpx.Request) -> httpx.Response:
        assert req.url.params["key"] == "dummy-key"
        if req.url.path.endswith("/metadata"):
            if deny:
                return httpx.Response(200, json={"status": "REQUEST_DENIED", "error_message": "API not enabled"})
            if not has_image:
                return httpx.Response(200, json={"status": "ZERO_RESULTS"})
            assert req.url.params["source"] == "outdoor"
            return httpx.Response(200, json={"status": "OK", "pano_id": "PANO1", "date": "2023-05",
                                             "copyright": "© 2026 Google", "location": {"lat": 34.7, "lng": 135.5}})
        assert req.url.params["pano"] == "PANO1"
        assert req.url.params["fov"] == "90"
        return httpx.Response(200, content=JPEG, headers={"content-type": "image/jpeg"})

    return StreetViewClient("dummy-key", http=httpx.Client(transport=httpx.MockTransport(handler)))


def load() -> Exploration:
    return Exploration.model_validate_json(FIXTURE.read_text(encoding="utf-8"))


def test_metadata_がOKなら画像を保存してrouteに書く(tmp_path: Path) -> None:
    e2, stats = fetch_images(make_client(), load(), tmp_path)
    assert stats.fetched == [0, 1] and stats.missing == []
    p = e2.points[0]
    assert p.image == "images/000.jpg"
    assert p.image_source == "street_view"
    assert p.street_view is not None and p.street_view.pano_id == "PANO1" and p.street_view.date == "2023-05"
    assert (tmp_path / "images" / "000.jpg").read_bytes() == JPEG


def test_画像が無い地点はnullのまま(tmp_path: Path) -> None:
    e2, stats = fetch_images(make_client(has_image=False), load(), tmp_path)
    assert stats.missing == [0, 1]
    assert all(p.image is None and p.street_view is None for p in e2.points)
    assert not (tmp_path / "images").exists()


def test_元のExplorationは変更されない(tmp_path: Path) -> None:
    e = load()
    e.points[0].image = None
    fetch_images(make_client(), e, tmp_path)
    assert e.points[0].image is None


def test_作成者の写真は触らない(tmp_path: Path) -> None:
    e = load()
    pts = [e.points[0].model_copy(update={"image": "photo.jpg", "image_source": "creator_photo"}), e.points[1]]
    e2, stats = fetch_images(make_client(), e.model_copy(update={"points": pts}), tmp_path)
    assert stats.skipped == [0]
    assert e2.points[0].image == "photo.jpg"


def test_REQUEST_DENIED_はエラー() -> None:
    with pytest.raises(StreetViewError, match="REQUEST_DENIED"):
        make_client(deny=True).metadata(34.7, 135.5)


def test_parse_metadata() -> None:
    assert parse_metadata({"status": "ZERO_RESULTS"}) is None
    m = parse_metadata({"status": "OK", "pano_id": "X", "location": {"lat": 1, "lng": 2}})
    assert m is not None and m.date is None and not m.is_official
    assert parse_metadata({"status": "OK", "pano_id": "Y", "copyright": "© 2026 Google"}).is_official


def test_offset_で手前の座標を指定する(tmp_path: Path) -> None:
    seen: list[str] = []

    def handler(req: httpx.Request) -> httpx.Response:
        if req.url.path.endswith("/metadata"):
            seen.append(req.url.params["location"])
            return httpx.Response(200, json={"status": "ZERO_RESULTS"})
        raise AssertionError

    client = StreetViewClient("k", http=httpx.Client(transport=httpx.MockTransport(handler)))
    p = load().points[0].model_copy(update={"maneuver": "TURN_RIGHT"})  # 出発点以外（出発点は前方に探す）
    e = load().model_copy(update={"points": [p]})
    fetch_images(client, e, tmp_path, StreetViewOptions(offset_m=10, search_tries=1))
    lat, lng = map(float, seen[0].split(","))
    # heading 85°（東寄り）に近づく → 手前は西側 → lng が小さくなる
    assert lng < p.lng and abs(lat - p.lat) < 0.0002


def test_公式パノラマを優先して手前を探す(tmp_path: Path) -> None:
    """最寄りがユーザー投稿なら、少し下がって公式を探す。"""
    calls: list[str] = []

    def handler(req: httpx.Request) -> httpx.Response:
        if req.url.path.endswith("/metadata"):
            calls.append(req.url.params["location"])
            n = len(calls)
            pano = {"status": "OK", "location": {"lat": 1, "lng": 2}}
            if n == 1:
                return httpx.Response(200, json={**pano, "pano_id": "USER", "copyright": "© someone"})
            return httpx.Response(200, json={**pano, "pano_id": "OFFICIAL", "copyright": "© 2026 Google"})
        return httpx.Response(200, content=JPEG, headers={"content-type": "image/jpeg"})

    client = StreetViewClient("k", http=httpx.Client(transport=httpx.MockTransport(handler)))
    e = load().model_copy(update={"points": [load().points[0]]})
    e2, _ = fetch_images(client, e, tmp_path, StreetViewOptions(search_step_m=8, search_tries=3))
    sv = e2.points[0].street_view
    assert sv is not None and sv.pano_id == "OFFICIAL" and sv.offset_m == 8.0
    assert len(calls) == 2


def test_公式が無ければ最初の投稿を使う(tmp_path: Path) -> None:
    def handler(req: httpx.Request) -> httpx.Response:
        if req.url.path.endswith("/metadata"):
            return httpx.Response(200, json={"status": "OK", "pano_id": "USER", "copyright": "© someone",
                                             "location": {"lat": 1, "lng": 2}})
        return httpx.Response(200, content=JPEG, headers={"content-type": "image/jpeg"})

    client = StreetViewClient("k", http=httpx.Client(transport=httpx.MockTransport(handler)))
    e = load().model_copy(update={"points": [load().points[0]]})
    e2, _ = fetch_images(client, e, tmp_path)
    assert e2.points[0].street_view is not None and e2.points[0].street_view.pano_id == "USER"



def test_camera_heading() -> None:
    p = load().points[0].model_copy(update={"heading": 350.0, "heading_out": 80.0})  # 北向きに進入 → 東へ右折
    assert camera_heading(p, "approach") == 350.0
    assert camera_heading(p, "departure") == 80.0
    assert camera_heading(p, "bisector") == 35.0  # 0 をまたいでも中間になる
    last = load().points[1]  # heading_out が無い（目的地）
    assert camera_heading(last, "bisector") == camera_heading(last, "approach")


def test_出発点は前方に探す(tmp_path: Path) -> None:
    seen: list[str] = []

    def handler(req: httpx.Request) -> httpx.Response:
        seen.append(req.url.params["location"])
        return httpx.Response(200, json={"status": "ZERO_RESULTS"})

    client = StreetViewClient("k", http=httpx.Client(transport=httpx.MockTransport(handler)))
    p = load().points[0].model_copy(update={"maneuver": "DEPART", "heading": 90.0})  # 東へ出発
    e = load().model_copy(update={"points": [p]})
    fetch_images(client, e, tmp_path, StreetViewOptions(search_tries=2, search_step_m=10))
    lng0 = float(seen[0].split(",")[1]); lng1 = float(seen[1].split(",")[1])
    assert lng1 > lng0  # 2 回目の候補は東（前方）


def test_候補は最大8枚_出発点と目的地は位置違いで複数(tmp_path: Path) -> None:
    from app.services.creator.streetview import fetch_candidates, variants_for, ENDPOINT_VARIANTS, TURN_VARIANTS
    n = 0

    def handler(req: httpx.Request) -> httpx.Response:
        nonlocal n
        if req.url.path.endswith("/metadata"):
            n += 1  # 位置ごとに別パノラマを返す
            return httpx.Response(200, json={"status": "OK", "pano_id": f"P{n}", "copyright": "© 2026 Google",
                                             "location": {"lat": 34.7, "lng": 135.5}})
        return httpx.Response(200, content=JPEG, headers={"content-type": "image/jpeg"})

    client = StreetViewClient("k", http=httpx.Client(transport=httpx.MockTransport(handler)))
    e = load()  # points[0] は DEPART、points[1] は ARRIVE
    assert variants_for(e.points[0]) is ENDPOINT_VARIANTS and variants_for(e.points[1]) is ENDPOINT_VARIANTS
    turn_pt = e.points[0].model_copy(update={"maneuver": "TURN_RIGHT", "heading_out": 170.0})
    assert variants_for(turn_pt) is TURN_VARIANTS
    e2, _ = fetch_candidates(client, e.model_copy(update={"polyline": ""}), tmp_path)  # 経路なし = 旧方式
    assert [len(p.candidates) for p in e2.points] == [8, 8]
    assert {c.image for c in e2.points[0].candidates} == {f"images/000_c{i}.jpg" for i in range(8)}


def test_同じパノラマからは3枚まで(tmp_path: Path) -> None:
    from app.services.creator.streetview import fetch_candidates

    def handler(req: httpx.Request) -> httpx.Response:
        if req.url.path.endswith("/metadata"):  # どこで聞いても同じパノラマ
            return httpx.Response(200, json={"status": "OK", "pano_id": "SAME", "copyright": "© 2026 Google",
                                             "location": {"lat": 34.7, "lng": 135.5}})
        return httpx.Response(200, content=JPEG, headers={"content-type": "image/jpeg"})

    client = StreetViewClient("k", http=httpx.Client(transport=httpx.MockTransport(handler)))
    e = load()
    turn_pt = e.points[0].model_copy(update={"maneuver": "TURN_RIGHT", "heading_out": 170.0})
    e2, _ = fetch_candidates(client, e.model_copy(update={"points": [turn_pt], "polyline": ""}), tmp_path)
    assert len(e2.points[0].candidates) == 3


# --- 経路があるとき: 進行方向だけ・経路上・曲がり角より手前 -------------------------------------

def _encode(points: list[tuple[float, float]]) -> str:
    out, prev = [], (0, 0)
    for lat, lng in points:
        cur = (round(lat * 1e5), round(lng * 1e5))
        for v in (cur[0] - prev[0], cur[1] - prev[1]):
            v = ~(v << 1) if v < 0 else v << 1
            while v >= 0x20:
                out.append(chr((0x20 | (v & 0x1F)) + 63)); v >>= 5
            out.append(chr(v + 63))
        prev = cur
    return "".join(out)


CORNER = (34.70000, 135.50200)
ROUTE = [(34.70000, 135.50000), CORNER, (34.70150, 135.50200)]  # 東へ約 180 m、角で左折して北へ


def _turn_exploration() -> Exploration:
    e = load()
    p = e.points[0].model_copy(update={"maneuver": "TURN_LEFT", "lat": CORNER[0], "lng": CORNER[1],
                                       "heading": 90.0, "heading_out": 0.0})
    return e.model_copy(update={"points": [p], "polyline": _encode(ROUTE)})


def _client(locate) -> StreetViewClient:
    """metadata は locate(要求座標) が返す位置にパノラマがあると答える。"""
    def handler(req: httpx.Request) -> httpx.Response:
        if req.url.path.endswith("/metadata"):
            lat, lng = (float(v) for v in req.url.params["location"].split(","))
            plat, plng = locate(lat, lng)
            return httpx.Response(200, json={"status": "OK", "pano_id": f"P{plat:.6f},{plng:.6f}",
                                             "copyright": "© 2026 Google", "location": {"lat": plat, "lng": plng}})
        assert req.url.params["fov"] == "90" and req.url.params["pitch"] == "0"
        return httpx.Response(200, content=JPEG, headers={"content-type": "image/jpeg"})
    return StreetViewClient("k", http=httpx.Client(transport=httpx.MockTransport(handler)))


def test_経路があれば進行方向だけを向き_角より手前から撮る(tmp_path: Path) -> None:
    from app.services.creator.streetview import TRAVEL_MODE, fetch_candidates
    e2, _ = fetch_candidates(_client(lambda lat, lng: (lat, lng)), _turn_exploration(), tmp_path)
    cands = e2.points[0].candidates
    assert len(cands) == 8
    assert all(c.heading_mode == TRAVEL_MODE for c in cands)
    assert all(abs(c.street_view.heading - 90.0) < 1.0 for c in cands)  # 曲がる先（北）へ回さない
    assert all(c.street_view.offset_m > 0 for c in cands)  # 角より手前


def test_経路から離れたパノラマは使わない(tmp_path: Path) -> None:
    from app.services.creator.streetview import fetch_candidates
    off = lambda lat, lng: (lat - 0.0003, lng)  # 約 33 m 南（別の道）
    e2, _ = fetch_candidates(_client(off), _turn_exploration(), tmp_path)
    assert e2.points[0].candidates == [] and e2.points[0].image is None


def test_角を越えた先のパノラマは使わない(tmp_path: Path) -> None:
    from app.services.creator.streetview import fetch_candidates
    past = lambda lat, lng: (CORNER[0] + 0.0002, CORNER[1])  # 角を曲がった先 約 22 m
    e2, _ = fetch_candidates(_client(past), _turn_exploration(), tmp_path)
    assert e2.points[0].candidates == []

"""手順 7〜9: 区間分割、区間ごとの経路、結合。Routes は合成データ。"""
from pathlib import Path

import httpx
import polyline as polyline_codec
import pytest

from app.external.google.routes import LatLng, Route, RoutesClient, RouteStep
from app.schemas.creator_input import CreatorPhoto, PlanInput
from app.schemas.exploration import Place
from app.services.creator.legs import merge_legs, plan_legs, split_legs
from app.services.creator.photos_map import render_photos_map
from app.services.creator.route import RouteOutput, decode_polyline
from app.services.creator.turns import extract_turns

ORIGIN = Place(query="S", lat=34.7000, lng=135.5000)
DEST = Place(query="G", lat=34.7020, lng=135.5040)


def photo(seq: int, lat: float, lng: float, **kw) -> CreatorPhoto:
    return CreatorPhoto(id=f"p{seq}", seq=seq, image=f"photos/p{seq}.jpg", lat=lat, lng=lng, **kw)


def synthetic_route(path: list[tuple[float, float]]) -> RouteOutput:
    """直線をつないだ経路。先頭ステップは DEPART、以降は方位差で判定される（maneuver 空）。"""
    enc = polyline_codec.encode(path, precision=5)
    steps = []
    for i in range(len(path) - 1):
        a, b = path[i], path[i + 1]
        steps.append(RouteStep(LatLng(*a), LatLng(*b), 100, "DEPART" if i == 0 else "", "進む", polyline_codec.encode([a, b], precision=5)))
    return RouteOutput(route=Route(distance_m=100 * (len(path) - 1), duration_s=60, polyline=enc, steps=steps), raw={})


# 写真 1 (B) で東→北 = 左折、写真 2 (C) で北→東 = 右折
A, B, C, D = (34.7000, 135.5000), (34.7000, 135.5020), (34.7020, 135.5020), (34.7020, 135.5040)
PHOTOS = [photo(0, *B), photo(1, *C, caption="赤いポスト")]


def test_split_legs_は写真順に区間を切る() -> None:
    legs = split_legs(ORIGIN, DEST, PHOTOS)
    assert [(l.start.query, l.end.query) for l in legs] == [("S", "写真 0"), ("写真 0", "写真 1"), ("写真 1", "G")]
    assert [l.photo_at_end.id if l.photo_at_end else None for l in legs] == ["p0", "p1", None]
    assert len(split_legs(ORIGIN, DEST, [])) == 1


def test_plan_legs_は区間ごとにAPIを叩き_失敗区間はNoneと警告() -> None:
    calls: list[tuple] = []

    def handler(req: httpx.Request) -> httpx.Response:
        import json
        body = json.loads(req.content)
        o, d = body["origin"]["location"]["latLng"], body["destination"]["location"]["latLng"]
        calls.append((o["latitude"], d["latitude"]))
        if o == d:
            return httpx.Response(200, json={"routes": []})
        return httpx.Response(200, json={"routes": [{"distanceMeters": 100, "duration": "60s",
                                                      "polyline": {"encodedPolyline": polyline_codec.encode([(o["latitude"], o["longitude"]), (d["latitude"], d["longitude"])], precision=5)},
                                                      "legs": [{"steps": []}]}]})

    client = RoutesClient("k", http=httpx.Client(transport=httpx.MockTransport(handler)))
    legs = split_legs(ORIGIN, DEST, [photo(0, *B), photo(1, *B)])  # 同じ場所に 2 枚 → 区間 1 は距離 0
    outputs, warnings = plan_legs(client, legs)
    assert len(calls) == 3 and outputs[1] is None and outputs[0] is not None and outputs[2] is not None
    assert len(warnings) == 1 and warnings[0].kind == "no_route" and warnings[0].photo_id == "p1"


def test_merge_legs_は写真地点を1つに統合し_向きと連続性を保つ() -> None:
    legs = split_legs(ORIGIN, DEST, PHOTOS)
    outputs = [synthetic_route([A, B]), synthetic_route([B, C]), synthetic_route([C, D])]
    merged = merge_legs(legs, outputs, ORIGIN, DEST)
    e = merged.exploration
    assert [p.index for p in e.points] == list(range(len(e.points)))
    creators = [p for p in e.points if p.image_source == "creator_photo"]
    assert [p.creator_photo.id for p in creators] == ["p0", "p1"]
    assert [p.turn for p in creators] == ["left", "right"]
    assert creators[1].instruction == "赤いポスト" and creators[1].landmark == "赤いポスト" and creators[0].instruction == "写真の地点"
    assert creators[0].image == "photos/p0.jpg" and creators[0].arrow_image is None
    assert e.points[0].maneuver == "DEPART" and e.points[-1].turn == "arrive"
    # 区間の境界で ARRIVE/DEPART が残っていない
    assert [p.maneuver for p in e.points] == ["DEPART", "CREATOR_PHOTO", "CREATOR_PHOTO", "ARRIVE"]
    # 距離は区間の合計、ポリラインは途切れず A→B→C→D
    assert e.total_distance_m == 300
    assert decode_polyline(e.polyline) == [A, B, C, D]
    assert sum(p.distance_to_next_m for p in e.points) > 0 and e.points[-1].distance_to_next_m == 0
    assert merged.warnings == []


def test_写真0枚なら従来のextract_turnsと同じ() -> None:
    out = synthetic_route([A, B, C])
    merged = merge_legs(split_legs(ORIGIN, DEST, []), [out], ORIGIN, DEST)
    assert merged.exploration == extract_turns(out.route, ORIGIN, DEST).exploration


def test_経路の無い区間は飛ばし_その写真は前の写真に統合される() -> None:
    photos = [photo(0, *B), photo(1, *B), photo(2, *C)]
    legs = split_legs(ORIGIN, DEST, photos)
    outputs = [synthetic_route([A, B]), None, synthetic_route([B, C]), synthetic_route([C, D])]
    merged = merge_legs(legs, outputs, ORIGIN, DEST)
    creators = [p.creator_photo.id for p in merged.exploration.points if p.creator_photo]
    assert creators == ["p0", "p2"]
    assert [w.photo_id for w in merged.warnings if w.kind == "no_route"] == ["p1"]
    assert decode_polyline(merged.exploration.polyline) == [A, B, C, D]


def test_撮影座標が経路から遠いと警告() -> None:
    far = photo(0, B[0] + 0.001, B[1], accuracy_m=10)  # 約 110 m 北
    legs = split_legs(ORIGIN, DEST, [far])
    outputs = [synthetic_route([A, B]), synthetic_route([B, D])]  # 経路側は B に吸着したとする
    merged = merge_legs(legs, outputs, ORIGIN, DEST)
    w = [w for w in merged.warnings if w.kind == "snapped_far"]
    assert len(w) == 1 and w[0].photo_id == "p0"
    cp = [p for p in merged.exploration.points if p.creator_photo][0].creator_photo
    assert cp.lat == far.lat and 100 < cp.snapped_m < 120  # 元の撮影座標は保持


def test_全区間で経路が無ければエラー() -> None:
    with pytest.raises(ValueError):
        merge_legs(split_legs(ORIGIN, DEST, []), [None], ORIGIN, DEST)


def test_写真順の地図は番号順に写真を載せる() -> None:
    plan = PlanInput(name="t", origin="S", destination="G", photos=PHOTOS)
    page = render_photos_map(plan, ORIGIN, DEST)
    assert page.index('"label": "S"') < page.index('"label": "0"') < page.index('"label": "1"') < page.index('"label": "G"')
    assert "photos/p0.jpg" in page and "赤いポスト" in page


# --- 目的地を省略すると最後の写真がゴール（会場の写真で終わる道） ---

def test_目的地なしなら最後の写真で区間が終わる() -> None:
    legs = split_legs(ORIGIN, None, PHOTOS)
    assert [(l.start.query, l.end.query) for l in legs] == [("S", "写真 0"), ("写真 0", "写真 1")]
    assert [l.photo_at_end.id for l in legs] == ["p0", "p1"]
    with pytest.raises(ValueError):
        split_legs(ORIGIN, None, [])


def test_目的地なしなら最後の写真が到着地点になる() -> None:
    legs = split_legs(ORIGIN, None, PHOTOS)
    goal = Place(query="赤いポスト", lat=C[0], lng=C[1])
    merged = merge_legs(legs, [synthetic_route([A, B]), synthetic_route([B, C])], ORIGIN, goal)
    e = merged.exploration
    assert [p.maneuver for p in e.points] == ["DEPART", "CREATOR_PHOTO", "CREATOR_PHOTO"]
    last = e.points[-1]
    assert last.turn == "arrive" and last.creator_photo.id == "p1" and last.image == "photos/p1.jpg"
    assert last.heading_out is None and last.distance_to_next_m == 0 and last.landmark == "赤いポスト"
    assert e.points[1].turn == "left"  # 途中の写真は今までどおり曲がる向きを持つ
    assert e.destination.query == "赤いポスト" and decode_polyline(e.polyline) == [A, B, C]
    assert merged.warnings == []


def test_PlanInputは目的地を省略できる_空文字も省略扱い_写真が無ければエラー() -> None:
    from app.schemas.creator_input import goal_from_last_photo

    base = {"name": "会場まで", "origin": "S", "photos": [p.model_dump() for p in PHOTOS]}
    plan = PlanInput.model_validate(base)
    assert plan.destination is None and plan.ends_at_last_photo
    assert PlanInput.model_validate({**base, "destination": "  "}).destination is None
    assert not PlanInput.model_validate({**base, "destination": "G"}).ends_at_last_photo
    goal = goal_from_last_photo(plan.photos[-1])
    assert (goal.query, goal.lat, goal.lng) == ("赤いポスト", C[0], C[1])
    assert goal_from_last_photo(plan.photos[0]).query == "最後の写真の地点"
    with pytest.raises(ValueError, match="写真が 1 枚以上"):
        PlanInput.model_validate({"name": "x", "origin": "S", "photos": []})

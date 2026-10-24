"""曲がり角抽出のロジックを、人工的な経路で確認する（API キー不要）。"""
import polyline as pl

from app.external.google.routes import LatLng, Route, RouteStep
from app.schemas.exploration import Place
from app.services.creator.turns import classify_turn, extract_turns

ORIGIN = Place(query="A", lat=34.7000, lng=135.5000)


def make_route(path: list[tuple[float, float]], steps: list[tuple[int, str, str]]) -> Route:
    """steps = [(開始頂点, maneuver, 案内文), ...]"""
    rs = []
    for k, (v, man, ins) in enumerate(steps):
        nv = steps[k + 1][0] if k + 1 < len(steps) else len(path) - 1
        rs.append(RouteStep(LatLng(*path[v]), LatLng(*path[nv]), 0, man, ins, ""))
    return Route(distance_m=0, duration_s=0, polyline=pl.encode(path), steps=rs)


def dest(path) -> Place:
    return Place(query="B", lat=path[-1][0], lng=path[-1][1])


def test_classify_turn() -> None:
    assert classify_turn("TURN_LEFT", None) == "left"
    assert classify_turn("TURN_SLIGHT_RIGHT", None) == "right"
    assert classify_turn("ARRIVE", None) == "arrive"
    assert classify_turn("", 45) == "right"
    assert classify_turn("", -45) == "left"
    assert classify_turn("", 10) == "straight"
    assert classify_turn("", 170) == "right"


def test_一本道のカーブは候補にならない() -> None:
    # 北→北東→東 と緩やかに曲がるが、ステップは 1 本（DEPART のみ）
    path = [(34.7000, 135.5000), (34.7005, 135.5000), (34.7009, 135.5003), (34.7011, 135.5008), (34.7011, 135.5014)]
    out = extract_turns(make_route(path, [(0, "DEPART", "北に進む")]), ORIGIN, dest(path))
    assert [p.turn for p in out.exploration.points] == ["straight", "arrive"]


def test_左折は採用される() -> None:
    path = [(34.7000, 135.5000), (34.7005, 135.5000), (34.7005, 135.4994)]  # 北 → 西
    out = extract_turns(make_route(path, [(0, "DEPART", ""), (1, "TURN_LEFT", "左折")]), ORIGIN, dest(path))
    assert [p.turn for p in out.exploration.points] == ["straight", "left", "arrive"]
    assert out.exploration.points[1].heading is not None and round(out.exploration.points[1].heading) == 0  # 北向きに近づく


def test_道路名が変わるだけなら不採用() -> None:
    path = [(34.7000, 135.5000), (34.7005, 135.5000), (34.7010, 135.5000)]  # 一直線
    out = extract_turns(make_route(path, [(0, "DEPART", ""), (1, "NAME_CHANGE", "○○通りに入る")]), ORIGIN, dest(path))
    assert [p.turn for p in out.exploration.points] == ["straight", "arrive"]
    rejected = [d for d in out.decisions if not d.accepted]
    assert len(rejected) == 1 and rejected[0].reason == "small_heading_change"


def test_案内文が無くても方位差が大きければ採用() -> None:
    path = [(34.7000, 135.5000), (34.7005, 135.5000), (34.7005, 135.5006)]  # 北 → 東
    out = extract_turns(make_route(path, [(0, "DEPART", ""), (1, "", "")]), ORIGIN, dest(path))
    assert [p.turn for p in out.exploration.points] == ["straight", "right", "arrive"]


def test_近すぎる候補は統合される() -> None:
    path = [(34.7000, 135.5000), (34.70002, 135.5000), (34.7005, 135.5000), (34.7005, 135.5006)]
    out = extract_turns(
        make_route(path, [(0, "DEPART", ""), (1, "STRAIGHT", "直進"), (2, "TURN_RIGHT", "右折")]), ORIGIN, dest(path)
    )
    assert [p.turn for p in out.exploration.points] == ["straight", "right", "arrive"]
    assert any(d.reason == "too_close" for d in out.decisions)


def test_作成者の写真は必ず採用() -> None:
    path = [(34.7000, 135.5000), (34.7005, 135.5000), (34.7010, 135.5000)]
    out = extract_turns(make_route(path, [(0, "DEPART", "")]), ORIGIN, dest(path), creator_photos=[(34.70051, 135.50001)])
    pts = out.exploration.points
    assert [p.turn for p in pts] == ["straight", "straight", "arrive"]
    assert pts[1].image_source == "creator_photo"


def test_距離は採用点の間で合算される() -> None:
    path = [(34.7000, 135.5000), (34.7005, 135.5000), (34.7010, 135.5000)]  # 約 55m + 55m
    out = extract_turns(make_route(path, [(0, "DEPART", ""), (1, "NAME_CHANGE", "")]), ORIGIN, dest(path))
    assert 105 < out.exploration.points[0].distance_to_next_m < 118
    assert out.exploration.points[-1].distance_to_next_m == 0


def test_目的地は直前の曲がり角に近くても採用() -> None:
    path = [(34.7000, 135.5000), (34.7005, 135.5000), (34.70052, 135.50003)]  # 最後の左折から数 m で到着
    out = extract_turns(make_route(path, [(0, "DEPART", ""), (1, "TURN_RIGHT", "右折")]), ORIGIN, dest(path))
    assert [p.turn for p in out.exploration.points] == ["straight", "right", "arrive"]

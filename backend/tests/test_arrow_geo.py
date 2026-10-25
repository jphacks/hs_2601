"""経路の投影による矢印の点列。"""
import math

import pytest

from app.imaging.projection import Camera, in_frame, project_ground
from app.schemas.exploration import ExplorationPoint, StreetViewMeta
from app.services.creator.arrow_geo import camera_position, geo_arrow_path, resample
from app.services.creator.geo import destination_point

CAM = (34.7000, 135.5000)


def test_正面の点は中央_遠いほど上に寄る() -> None:
    cam = Camera(*CAM, heading=0.0, fov=90.0)
    near = project_ground(cam, destination_point(CAM, 0.0, 5.0))
    far = project_ground(cam, destination_point(CAM, 0.0, 40.0))
    assert near and far
    assert abs(near[0] - 0.5) < 0.01 and abs(far[0] - 0.5) < 0.01
    assert near[1] > far[1] > 0.5  # 地面はすべて水平線（0.5）より下


def test_画角の端と外_後ろ() -> None:
    cam = Camera(*CAM, heading=0.0, fov=90.0)
    right_edge = project_ground(cam, destination_point(CAM, 45.0, 20.0))
    assert right_edge and abs(right_edge[0] - 1.0) < 0.01
    outside = project_ground(cam, destination_point(CAM, 70.0, 20.0))
    assert outside and not in_frame(outside)
    assert project_ground(cam, destination_point(CAM, 180.0, 20.0)) is None


def test_pitchを上げると地面は下に写る() -> None:
    pt = destination_point(CAM, 0.0, 20.0)
    flat = project_ground(Camera(*CAM, heading=0.0, pitch=0.0), pt)
    up = project_ground(Camera(*CAM, heading=0.0, pitch=10.0), pt)
    assert flat and up and up[1] > flat[1]


def test_resample_は等間隔に刻む() -> None:
    path = [CAM, destination_point(CAM, 90.0, 100.0)]
    pts = resample(path, 10.0, 30.0, 5.0)
    assert len(pts) == 5
    assert abs(pts[0][1] - destination_point(CAM, 90.0, 10.0)[1]) < 1e-6


def point(turn: str, heading_in: float, heading_out: float, at) -> ExplorationPoint:
    return ExplorationPoint(index=1, lat=at[0], lng=at[1], heading=heading_in, heading_out=heading_out, maneuver="TURN",
                            turn=turn, instruction="", distance_to_next_m=50)


def test_左折の経路を手前から見ると左へ曲がる点列になる() -> None:
    corner = destination_point(CAM, 0.0, 25.0)  # カメラの 25 m 先で北→西へ曲がる
    path = [destination_point(CAM, 180.0, 40.0), corner, destination_point(corner, 270.0, 40.0)]
    sv = StreetViewMeta(pano_id="P", heading=0.0, fov=90, lat=CAM[0], lng=CAM[1])
    pts = geo_arrow_path(path, point("left", 0.0, 270.0, corner), sv)
    assert pts and len(pts) >= 3  # 足元 → 曲がり角 → 左（直線上の点は間引かれる）
    assert all(0 <= x <= 1 and 0 <= y <= 1 for x, y in pts)
    assert pts[0][1] >= 0.9 and pts[-1][0] < 0.3  # 足元から始まり、終点は左側
    ys = [y for _, y in pts]
    assert all(b <= a + 1e-6 for a, b in zip(ys, ys[1:]))  # 奥へ行くほど上（横へ進む間は同じ高さ）


def test_カメラが後ろを向いていれば手前へ戻る区間しか無いのでNone() -> None:
    corner = destination_point(CAM, 0.0, 25.0)
    path = [destination_point(CAM, 180.0, 40.0), corner, destination_point(corner, 270.0, 40.0)]
    sv = StreetViewMeta(pano_id="P", heading=180.0, fov=90, lat=CAM[0], lng=CAM[1])  # 来た道を向く
    assert geo_arrow_path(path, point("left", 0.0, 270.0, corner), sv) is None


def test_曲がった先に置かれたカメラでは先の道だけが描かれる() -> None:
    corner = destination_point(CAM, 0.0, 25.0)
    path = [destination_point(CAM, 180.0, 40.0), corner, destination_point(corner, 270.0, 40.0)]
    cam = destination_point(corner, 270.0, 8.0)  # 曲がった先 8 m、西向き
    sv = StreetViewMeta(pano_id="P", heading=270.0, fov=90, lat=cam[0], lng=cam[1], offset_m=-8.0)
    pts = geo_arrow_path(path, point("left", 0.0, 270.0, corner), sv)
    assert pts and all(abs(x - 0.5) < 0.05 for x, _ in pts[1:])  # 正面にまっすぐ


def test_位置が無いメタはoffsetから推定する() -> None:
    p = point("left", 0.0, 270.0, CAM)
    back = camera_position(p, StreetViewMeta(pano_id="P", heading=0.0, offset_m=20.0))
    assert abs(back[0] - destination_point(CAM, 180.0, 20.0)[0]) < 1e-9  # 進入方向の手前
    ahead = camera_position(p, StreetViewMeta(pano_id="P", heading=270.0, offset_m=-10.0))
    assert abs(ahead[1] - destination_point(CAM, 270.0, 10.0)[1]) < 1e-9  # 曲がった先
    exact = camera_position(p, StreetViewMeta(pano_id="P", heading=0.0, lat=1.0, lng=2.0))
    assert exact == (1.0, 2.0)


def test_候補選定は経路が足元から曲がり角まで見える候補を優先する() -> None:
    from app.schemas.exploration import ImageCandidate, VlmScore
    from app.services.creator.landmark import choose_best

    corner = destination_point(CAM, 0.0, 25.0)
    path = [destination_point(CAM, 180.0, 40.0), corner, destination_point(corner, 270.0, 40.0)]
    p = point("left", 0.0, 270.0, corner)
    good = StreetViewMeta(pano_id="A", heading=0.0, fov=90, lat=CAM[0], lng=CAM[1])  # 手前から曲がり角を見る
    beyond = destination_point(corner, 270.0, 8.0)
    past = StreetViewMeta(pano_id="B", heading=270.0, fov=90, lat=beyond[0], lng=beyond[1], offset_m=-8.0)  # 曲がった先
    back = StreetViewMeta(pano_id="C", heading=180.0, fov=90, lat=CAM[0], lng=CAM[1])  # 後ろ向き
    hi = VlmScore(here=5, arrow=5)
    lo = VlmScore(here=3, arrow=3)
    cands = [ImageCandidate(image="b", heading_mode="departure", street_view=past, score=hi),
             ImageCandidate(image="c", heading_mode="x", street_view=back, score=hi),
             ImageCandidate(image="a", heading_mode="approach", street_view=good, score=lo)]
    assert choose_best(cands, 0, p, path) == 2  # 点数が低くても、道なりが見える候補
    assert choose_best(cands, 0) == 0  # 経路情報なしなら従来どおりモデルの選択


def test_カメラの脇を通る経路は枠の縁から線を始める() -> None:
    from app.services.creator.arrow_geo import clip_to_frame, geo_arrow_path

    assert clip_to_frame((0.9, 1.1), (0.7, 0.8)) == pytest.approx((0.8333, 1.0), abs=1e-3)
    assert clip_to_frame((-0.5, 0.8), (0.5, 0.8)) == pytest.approx((0.0, 0.8))
    assert clip_to_frame((1.5, 1.5), (0.5, 0.5)) == pytest.approx((1.0, 1.0))  # 角から入る
    assert clip_to_frame((1.3, 1.1), (0.5, 0.7)) == pytest.approx((1.0, 0.95))  # 右端から入る（遅い方の交点）
    corner = destination_point(CAM, 0.0, 25.0)
    # 経路はカメラの 12 m 右を通る（寄せる距離 SNAP_M より遠い = 経路の上に立っていない）
    side = destination_point(CAM, 90.0, 12.0)
    path = [destination_point(side, 180.0, 40.0), destination_point(corner, 90.0, 12.0), destination_point(corner, 270.0, 40.0)]
    sv = StreetViewMeta(pano_id="P", heading=0.0, fov=90, lat=CAM[0], lng=CAM[1])
    pts = geo_arrow_path(path, point("left", 0.0, 270.0, corner), sv)
    assert pts
    x0, y0 = pts[0]
    assert (y0 == 1.0 or x0 == 1.0) and x0 > 0.5  # 足元の中央ではなく、右の縁から入ってくる
    assert pts[1][0] <= x0  # 縁から奥へ向かって折り返さない（ジグザグにならない）


def test_simplify_は直線上の点と小さなブレを落とす() -> None:
    from app.services.creator.arrow_geo import simplify

    line = [(0.5, 0.95), (0.5, 0.85), (0.5, 0.75), (0.5, 0.65)]
    assert simplify(line) == [(0.5, 0.95), (0.5, 0.65)]
    wobble = [(0.5, 0.95), (0.5, 0.8), (0.505, 0.6), (0.495, 0.55), (0.5, 0.52), (0.2, 0.5)]
    out = simplify(wobble)
    assert out[0] == wobble[0] and out[-1] == wobble[-1]
    assert len(out) == 3  # 直進 → 曲がり角 → 左へ


def test_候補選定は公式撮影を優先する() -> None:
    from app.schemas.exploration import ImageCandidate, VlmScore
    from app.services.creator.landmark import choose_best

    corner = destination_point(CAM, 0.0, 25.0)
    path = [destination_point(CAM, 180.0, 40.0), corner, destination_point(corner, 270.0, 40.0)]
    p = point("left", 0.0, 270.0, corner)
    user = StreetViewMeta(pano_id="U", heading=0.0, fov=90, lat=CAM[0], lng=CAM[1], copyright="© Taro")
    official = StreetViewMeta(pano_id="G", heading=0.0, fov=90, lat=CAM[0], lng=CAM[1], copyright="© 2026 Google")
    cands = [ImageCandidate(image="u", heading_mode="approach", street_view=user, score=VlmScore(here=5, arrow=5)),
             ImageCandidate(image="g", heading_mode="approach", street_view=official, score=VlmScore(here=3, arrow=3))]
    assert choose_best(cands, 0, p, path) == 1


def test_経路の数m脇に立つカメラは経路の上に寄せて足元から線を引く() -> None:
    from app.services.creator.arrow_geo import geo_arrow_path
    corner = destination_point(CAM, 0.0, 25.0)
    side = destination_point(CAM, 90.0, 4.0)  # 地図の経路線が 4 m 右にずれている
    path = [destination_point(side, 180.0, 40.0), destination_point(corner, 90.0, 4.0), destination_point(corner, 270.0, 40.0)]
    sv = StreetViewMeta(pano_id="P", heading=0.0, fov=90, lat=CAM[0], lng=CAM[1])
    pts = geo_arrow_path(path, point("left", 0.0, 270.0, corner), sv)
    assert pts
    x0, y0 = pts[0]
    assert y0 >= 0.9 and abs(x0 - 0.5) < 0.05  # 足元の中央から始まる
    assert pts[-1][0] < 0.3  # 左折なので左へ抜ける

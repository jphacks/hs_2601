"""VLM に渡す経路情報・撮影位置の文章。"""
from app.schemas.exploration import ExplorationPoint, ImageCandidate, StreetViewMeta
from app.services.creator.geo import destination_point
from app.services.creator.landmark import build_prompt
from app.services.creator.vlm_context import candidate_context, compass, relative, route_context, route_profile

CAM = (34.7000, 135.5000)
CORNER = destination_point(CAM, 0.0, 25.0)
PATH = [destination_point(CAM, 180.0, 40.0), CORNER, destination_point(CORNER, 270.0, 40.0)]


def point() -> ExplorationPoint:
    return ExplorationPoint(index=1, lat=CORNER[0], lng=CORNER[1], heading=0.0, heading_out=270.0, maneuver="TURN",
                            turn="left", instruction="左折", distance_to_next_m=40)


def test_方位の言葉() -> None:
    assert compass(0) == "北" and compass(44) == "北東" and compass(359) == "北" and compass(225) == "南西"
    assert relative(0.0, 35.0) == "右 35°" and relative(0.0, 325.0) == "左 35°"
    assert relative(10.0, 15.0) == "ほぼ同じ向き" and relative(0.0, 180.0).startswith("後ろ向き")


def test_経路情報には座標_方位_前後の経路が入る() -> None:
    text = route_context(point(), PATH)
    assert f"({CORNER[0]:.6f}, {CORNER[1]:.6f})" in text
    assert "進入方位（この地点へ歩いて来る向き）: 0°（北）" in text
    assert "退出方位（この地点から進む向き）: 270°（西）" in text
    assert "向きの変化: 左 90°" in text
    assert "20 m 手前" in text and "20 m 先" in text and "次へ進む方位 270°（西）" in text
    prof = route_profile(PATH, point())
    assert [o for o, _, _ in prof][:3] == [-60.0, -40.0, -20.0]
    assert prof[-1][0] == 40.0  # 曲がった先 40 m まで（経路の末端）


def test_候補ごとに撮影位置_向き_投影線が入る() -> None:
    before = StreetViewMeta(pano_id="A", heading=0.0, fov=90, lat=CAM[0], lng=CAM[1], copyright="© 2026 Google", date="2024-05")
    beyond = destination_point(CORNER, 270.0, 8.0)
    after = StreetViewMeta(pano_id="B", heading=270.0, fov=90, lat=beyond[0], lng=beyond[1], copyright="© Taro")
    back = StreetViewMeta(pano_id="C", heading=180.0, fov=90, lat=CAM[0], lng=CAM[1])
    cands = [ImageCandidate(image="a", heading_mode="approach", street_view=before),
             ImageCandidate(image="b", heading_mode="departure", street_view=after),
             ImageCandidate(image="c", heading_mode="x", street_view=back)]
    text = candidate_context(point(), cands, PATH)
    assert "画像 0: 撮影位置" in text and "交差点の 25 m 手前" in text
    assert "カメラの向き: 0°（北）、進入方位から見て ほぼ同じ向き、水平画角 90°、ピッチ 0°" in text
    assert "Google 公式、2024-05" in text and "ユーザー投稿" in text
    assert "曲がる地点の画像内座標: (0.50, 0.55)" in text
    assert "経路の投影線（歩行者が通る路面の中心線を画像座標に写したもの）: (0.50, 0.92)" in text
    assert "曲がった先の道路に 8 m 入った位置" in text and "進入方位から見て 左 90°" in text
    assert "後ろ向き" in text and "この画像には歩く向きの経路が映らない" in text


def test_プロンプトに経路情報と画像情報が埋まる() -> None:
    sv = StreetViewMeta(pano_id="A", heading=0.0, fov=90, lat=CAM[0], lng=CAM[1])
    p = point().model_copy(update={"candidates": [ImageCandidate(image="a", heading_mode="approach", street_view=sv)]})
    prompt = build_prompt(p, 1, route=PATH)
    assert "## 経路情報" in prompt and "退出方位" in prompt and "画像 0: 撮影位置" in prompt and "経路の投影線" in prompt
    assert "{route_info}" not in prompt and "{images_info}" not in prompt
    assert '{"evaluations"' in prompt  # 出力例の波括弧がそのまま残る
    # 経路が無くても組み立てられる（候補の位置・向きだけ入る）
    assert "前後の経路" not in build_prompt(p, 1)

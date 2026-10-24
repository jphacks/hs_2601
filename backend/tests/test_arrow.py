from io import BytesIO
from pathlib import Path

from PIL import Image

from app.imaging.arrow import catmull_rom, default_path, draw_arrow
from app.schemas.exploration import ArrowPoint, Exploration, ImageCandidate, StreetViewMeta, VlmScore
from app.services.creator.arrow import arrow_path_for, draw_arrows, ensure_turn_side

FIXTURE = Path(__file__).parent / "fixtures" / "route_sample.json"


def blank_jpeg(w: int = 200, h: int = 200) -> bytes:
    buf = BytesIO()
    Image.new("RGB", (w, h), (120, 120, 120)).save(buf, format="JPEG")
    return buf.getvalue()


def test_曲線は制御点を通り滑らかに補間される() -> None:
    pts = [(0.5, 0.95), (0.5, 0.6), (0.2, 0.5)]
    curve = catmull_rom(pts, samples_per_segment=8)
    assert curve[0] == pts[0] and curve[-1] == pts[-1]
    assert len(curve) > len(pts)


def test_矢印を描くと画像が変わりサイズは同じ() -> None:
    src = blank_jpeg()
    out = draw_arrow(src, [(0.5, 0.95), (0.5, 0.6), (0.2, 0.5)], "left")
    a, b = Image.open(BytesIO(src)), Image.open(BytesIO(out))
    assert a.size == b.size
    assert a.tobytes() != b.tobytes()
    # 終点付近（左）に橙系の色が乗っている
    r, g, bl = b.getpixel((int(0.2 * 200), int(0.5 * 200)))
    assert r > 150 and bl < 120


def test_経路が無ければ既定形() -> None:
    assert default_path("right")[-1][0] > 0.8
    assert default_path("left")[-1][0] < 0.2
    assert default_path("straight")[-1][1] < default_path("straight")[0][1]


def test_VLMの経路があればそれを使う(tmp_path: Path) -> None:
    e = Exploration.model_validate_json(FIXTURE.read_text(encoding="utf-8"))
    (tmp_path / "images").mkdir()
    (tmp_path / "images" / "000_c0.jpg").write_bytes(blank_jpeg())
    score = VlmScore(landmark=4, turn=4, arrow=5, arrow_path=[ArrowPoint(x=0.5, y=0.9), ArrowPoint(x=0.5, y=0.6), ArrowPoint(x=0.9, y=0.5)])
    cand = ImageCandidate(image="images/000_c0.jpg", heading_mode="bisector", street_view=StreetViewMeta(pano_id="P", heading=0), score=score)
    p0 = e.points[0].model_copy(update={"image": cand.image, "candidates": [cand], "chosen_candidate": 0, "turn": "right"})
    p1 = e.points[1].model_copy(update={"image": None})
    e2, stats = draw_arrows(e.model_copy(update={"points": [p0, p1]}), tmp_path)
    assert arrow_path_for(p0) == ([(0.5, 0.9), (0.5, 0.6), (0.9, 0.5)], True)
    assert e2.points[0].arrow_image == "images/000_arrow.jpg"
    assert (tmp_path / "images" / "000_arrow.jpg").exists()
    assert stats.drawn == [0] and stats.with_vlm_path == [0] and stats.skipped == [1]
    assert e.points[0].arrow_image is None  # 元は変更されない


def test_左折なのにまっすぐな経路は左へ曲げる() -> None:
    straight = [(0.5, 0.95), (0.5, 0.7), (0.5, 0.55)]
    bent = ensure_turn_side(straight, "left")
    assert bent[-1][0] <= 0.3 and bent[-1][1] == 0.55 and len(bent) == 4
    assert ensure_turn_side(straight, "straight") == straight
    assert ensure_turn_side([(0.5, 0.95), (0.8, 0.5)], "right") == [(0.5, 0.95), (0.8, 0.5)]  # すでに右なら触らない

"""地図の案内線と VLM の線の突き合わせ（arrow_fuse）と、矢印の線の選び方（arrow.arrow_path_for）。"""
from io import BytesIO

from PIL import Image

from app.imaging.guide import draw_guide
from app.services.creator.arrow_fuse import consistent, deviation

GEO_LEFT = [(0.55, 0.95), (0.55, 0.75), (0.53, 0.6), (0.3, 0.57), (0.1, 0.55)]


def test_案内線に沿って少し横にずれたVLMの線は採用する() -> None:
    vlm = [(0.5, 0.95), (0.5, 0.75), (0.49, 0.62), (0.3, 0.6), (0.1, 0.58)]
    mean, worst = deviation(vlm, GEO_LEFT)
    assert mean < 0.06 and worst < 0.1
    assert consistent(vlm, GEO_LEFT, "left")


def test_別の道へ引いたVLMの線は採用しない() -> None:
    other_road = [(0.5, 0.95), (0.5, 0.8), (0.5, 0.4), (0.3, 0.3), (0.1, 0.28)]  # ずっと奥で曲がる
    assert not consistent(other_road, GEO_LEFT, "left")


def test_曲がる向きが違うVLMの線は採用しない() -> None:
    right = [(0.5, 0.95), (0.52, 0.75), (0.54, 0.6), (0.7, 0.57), (0.9, 0.55)]
    assert not consistent(right, GEO_LEFT, "left")


def test_足元から始まらないVLMの線は採用しない() -> None:
    floating = [(0.55, 0.6), (0.3, 0.57), (0.1, 0.55)]
    assert not consistent(floating, GEO_LEFT, "left")


def test_案内線を重ねた画像は同じ大きさのJPEG() -> None:
    buf = BytesIO()
    Image.new("RGB", (64, 48), "gray").save(buf, format="JPEG")
    out = draw_guide(buf.getvalue(), GEO_LEFT, (0.53, 0.6))
    im = Image.open(BytesIO(out))
    assert im.format == "JPEG" and im.size == (64, 48)

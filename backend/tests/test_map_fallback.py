"""Street View が無い地点に地図画像を付ける（map_fallback）。写真なしの地点を作らない。"""
from io import BytesIO
from pathlib import Path

from PIL import Image

from app.imaging.route_tile_map import OUT_H, OUT_W
from app.schemas.exploration import Exploration
from app.services.creator.map_fallback import add_map_images

FIXTURE = Path(__file__).parent / "fixtures" / "route_sample.json"


def _tile(z: int, x: int, y: int) -> bytes:
    buf = BytesIO()
    Image.new("RGB", (256, 256), (200, 220, 200)).save(buf, format="PNG")
    return buf.getvalue()


def test_画像の無い地点に地図画像を付ける(tmp_path: Path) -> None:
    e = Exploration.model_validate_json(FIXTURE.read_text(encoding="utf-8"))
    pts = [e.points[0].model_copy(update={"image": None, "image_source": None, "arrow_image": None}),
           e.points[1].model_copy(update={"image": "images/x.jpg", "image_source": "street_view"})]
    e2, stats = add_map_images(e.model_copy(update={"points": pts}), tmp_path, _tile)
    assert stats.drawn == [0]
    p = e2.points[0]
    assert p.image == p.arrow_image == "images/000_map.png" and p.image_source == "map"
    im = Image.open(tmp_path / p.image)
    assert im.format == "PNG" and im.size == (OUT_W, OUT_H)
    assert e2.points[1].image == "images/x.jpg"  # 画像のある地点は触らない


def test_タイルが取れなくても画像は作る(tmp_path: Path) -> None:
    e = Exploration.model_validate_json(FIXTURE.read_text(encoding="utf-8"))
    pts = [p.model_copy(update={"image": None, "image_source": None}) for p in e.points]
    e2, stats = add_map_images(e.model_copy(update={"points": pts}), tmp_path, lambda z, x, y: None)
    assert stats.drawn == [0, 1] and all((tmp_path / p.image).is_file() for p in e2.points)


def test_作成者の写真の地点は触らない(tmp_path: Path) -> None:
    e = Exploration.model_validate_json(FIXTURE.read_text(encoding="utf-8"))
    pts = [e.points[0].model_copy(update={"image": None, "image_source": "creator_photo"})]
    e2, stats = add_map_images(e.model_copy(update={"points": pts}), tmp_path, _tile)
    assert stats.drawn == [] and e2.points[0].image is None

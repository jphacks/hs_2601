"""手順 1・2: 作成入力 photos.json の検証と、写真の正規化。"""
import json
from io import BytesIO
from pathlib import Path

import pytest
from PIL import Image

from app.schemas.creator_input import PlanInput
from app.services.creator.photos import PlanInputError, load_plan_input, normalize_photo


def plan(**over) -> dict:
    base = {
        "name": "テスト", "origin": "大阪駅", "destination": "グランフロント大阪",
        "photos": [
            {"id": "p0", "seq": 0, "image": "photos/p0.jpg", "lat": 34.70, "lng": 135.49, "accuracy_m": 8},
            {"id": "p1", "seq": 1, "image": "photos/p1.jpg", "lat": 34.71, "lng": 135.50, "caption": "赤い看板"},
        ],
    }
    return {**base, **over}


def test_地名だけの出発地は座標なしのPlaceになる() -> None:
    p = PlanInput.model_validate(plan())
    assert p.origin.query == "大阪駅" and p.origin.lat is None
    assert p.photos[1].caption == "赤い看板" and p.photos[0].location_source == "gps"
    assert p.options.use_vlm_on_photos is False


def test_座標付きの出発地も書ける() -> None:
    p = PlanInput.model_validate(plan(origin={"query": "現在地", "lat": 34.7, "lng": 135.5}))
    assert p.origin.lat == 34.7


@pytest.mark.parametrize("bad", [
    {"origin": {"query": "x", "lat": 34.7}},                       # lng 欠け
    {"name": "  "},                                                 # 命名が空白
    {"photos": [{"id": "a", "seq": 1, "image": "photos/a.jpg", "lat": 0, "lng": 0}]},   # seq が 0 から始まらない
    {"photos": [{"id": "a", "seq": 0, "image": "../a.jpg", "lat": 0, "lng": 0}]},       # photos/ の外
    {"photos": [{"id": "a", "seq": 0, "image": "photos/a.jpg", "lat": 99, "lng": 0}]},  # 緯度の範囲外
    {"photos": [{"id": "a", "seq": 0, "image": "photos/a.jpg", "lat": 0, "lng": 0},
                {"id": "a", "seq": 1, "image": "photos/b.jpg", "lat": 0, "lng": 0}]},  # id 重複
])
def test_不正な入力は拒否する(bad: dict) -> None:
    with pytest.raises(ValueError):
        PlanInput.model_validate(plan(**bad))


def test_写真0枚でも有効() -> None:
    assert PlanInput.model_validate(plan(photos=[])).photos == []


def write_jpeg(path: Path, size=(40, 30), orientation: int | None = None) -> None:
    img = Image.new("RGB", size, "white")
    kw = {}
    if orientation:
        exif = Image.Exif()
        exif[274] = orientation
        kw["exif"] = exif.tobytes()
    path.parent.mkdir(parents=True, exist_ok=True)
    img.save(path, format="JPEG", **kw)


def test_load_plan_input_は画像の存在まで確かめる(tmp_path: Path) -> None:
    (tmp_path / "photos.json").write_text(json.dumps(plan(), ensure_ascii=False), encoding="utf-8")
    with pytest.raises(PlanInputError, match="写真ファイルがありません"):
        load_plan_input(tmp_path)
    write_jpeg(tmp_path / "photos" / "p0.jpg")
    write_jpeg(tmp_path / "photos" / "p1.jpg")
    assert len(load_plan_input(tmp_path).photos) == 2


def test_load_plan_input_はファイル無しと形式不正を区別して伝える(tmp_path: Path) -> None:
    with pytest.raises(PlanInputError, match="ありません"):
        load_plan_input(tmp_path)
    (tmp_path / "photos.json").write_text("{\"name\": \"\"}", encoding="utf-8")
    with pytest.raises(PlanInputError, match="形式が不正"):
        load_plan_input(tmp_path)


def test_normalize_photo_はEXIFの回転を適用し長辺を縮める(tmp_path: Path) -> None:
    src = tmp_path / "big.jpg"
    write_jpeg(src, size=(4000, 3000), orientation=6)  # 6 = 時計回りに 90°
    out = Image.open(BytesIO(normalize_photo(src.read_bytes())))
    assert out.format == "JPEG" and out.size == (960, 1280)  # 回転して縦長、長辺 1280
    assert out.getexif().get(274) in (None, 1)


def test_normalize_photo_は小さい画像を拡大しない(tmp_path: Path) -> None:
    src = tmp_path / "small.jpg"
    write_jpeg(src, size=(40, 30))
    assert Image.open(BytesIO(normalize_photo(src.read_bytes()))).size == (40, 30)


def test_normalize_photo_は画像でなければエラー() -> None:
    with pytest.raises(PlanInputError, match="開けません"):
        normalize_photo(b"not an image")

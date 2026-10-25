"""作成入力（photos.json）の読み込みと、写真の正規化。

- ``load_plan_input(dir)``: ``dir/photos.json`` を検証して読み、画像ファイルの存在も確かめる。
- ``normalize_photo(bytes)``: EXIF の回転を適用し、長辺を ``MAX_EDGE`` px に収めて JPEG で返す。
  スマホの原寸（数千 px、数 MB）をそのまま流さないため。HEIC など開けない形式はエラー。
"""
from __future__ import annotations

from io import BytesIO
from pathlib import Path

from PIL import Image, ImageOps, UnidentifiedImageError

from app.schemas.creator_input import PlanInput

PHOTOS_JSON = "photos.json"
MAX_EDGE = 1280
JPEG_QUALITY = 88


class PlanInputError(ValueError):
    pass


def load_plan_input(input_dir: Path) -> PlanInput:
    path = input_dir / PHOTOS_JSON
    if not path.exists():
        raise PlanInputError(f"{path} がありません")
    try:
        plan = PlanInput.model_validate_json(path.read_text(encoding="utf-8"))
    except ValueError as e:
        raise PlanInputError(f"{path} の形式が不正です: {e}") from e
    missing = [p.image for p in plan.photos if not (input_dir / p.image).is_file()]
    if missing:
        raise PlanInputError(f"写真ファイルがありません: {', '.join(missing)}")
    return plan


def normalize_photo(data: bytes, *, max_edge: int = MAX_EDGE) -> bytes:
    try:
        img = Image.open(BytesIO(data))
        img.load()
    except (UnidentifiedImageError, OSError) as e:
        raise PlanInputError("画像を開けません（JPEG か PNG にしてください。HEIC は非対応）") from e
    img = ImageOps.exif_transpose(img) or img
    img = img.convert("RGB")
    w, h = img.size
    scale = max_edge / max(w, h)
    if scale < 1:
        img = img.resize((max(1, round(w * scale)), max(1, round(h * scale))), Image.LANCZOS)
    buf = BytesIO()
    img.save(buf, format="JPEG", quality=JPEG_QUALITY)
    return buf.getvalue()

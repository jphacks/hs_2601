"""作成受付（POST /api/routes）の入力検査と、作業ディレクトリへの書き出し。

- manifest（PlanInput の JSON 文字列）と、``<id>.jpg`` の写真ファイルを突き合わせる。
- 写真は normalize_photo（EXIF 回転・長辺 1280px・JPEG）にしてから ``photos/<id>.jpg`` に置き、manifest を ``photos.json`` にする。
- 不正な入力は PlanInputError（API では 400）。メッセージはそのまま利用者に見せる。
"""
from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

from pydantic import ValidationError

from app.schemas.creator_input import PlanInput
from app.services.creator.photos import PHOTOS_JSON, PlanInputError, normalize_photo

MAX_PHOTOS = 50
MAX_PHOTO_BYTES = 15 * 1024 * 1024  # 1 枚あたり。フロントで縮小して送る前提なので十分に大きい


@dataclass(frozen=True)
class UploadedPhoto:
    filename: str
    data: bytes


def _first_error(e: ValidationError) -> str:
    err = e.errors()[0]
    loc = ".".join(str(x) for x in err["loc"]) or "manifest"
    return f"{loc}: {err['msg']}"


def parse_manifest(text: str | None) -> PlanInput:
    if not text:
        raise PlanInputError("manifest がありません")
    try:
        plan = PlanInput.model_validate_json(text)
    except ValidationError as e:
        raise PlanInputError(f"manifest の形式が不正です（{_first_error(e)}）") from e
    if not (plan.creator_id or "").strip():
        raise PlanInputError("manifest の creator_id がありません")
    if len(plan.photos) > MAX_PHOTOS:
        raise PlanInputError(f"写真は {MAX_PHOTOS} 枚までです")
    return plan


def match_photos(plan: PlanInput, files: list[UploadedPhoto]) -> dict[str, bytes]:
    """manifest の ``photos[].image`` のファイル名と、送られたファイル名を 1 対 1 に突き合わせる。返りは image → 中身。"""
    names = [f.filename for f in files]
    if len(set(names)) != len(names):
        raise PlanInputError("同じ名前の写真ファイルが複数あります")
    by_name = {f.filename: f.data for f in files}
    expected = {PurePosixPath(p.image).name: p.image for p in plan.photos}
    missing = sorted(set(expected) - set(by_name))
    extra = sorted(set(by_name) - set(expected))
    if missing:
        raise PlanInputError(f"写真ファイルが足りません: {', '.join(missing)}")
    if extra:
        raise PlanInputError(f"manifest に無い写真ファイルがあります: {', '.join(extra)}")
    too_big = [n for n, d in by_name.items() if len(d) > MAX_PHOTO_BYTES]
    if too_big:
        raise PlanInputError(f"写真ファイルが大きすぎます（1 枚 {MAX_PHOTO_BYTES // (1024 * 1024)} MB まで）: {', '.join(too_big)}")
    return {expected[n]: d for n, d in by_name.items()}


def normalize_photos(photos: dict[str, bytes]) -> dict[str, bytes]:
    """全部を正規化する。開けない画像があれば、どのファイルかを添えて PlanInputError。"""
    out: dict[str, bytes] = {}
    for image, data in photos.items():
        try:
            out[image] = normalize_photo(data)
        except PlanInputError as e:
            raise PlanInputError(f"{PurePosixPath(image).name}: {e}") from e
    return out


def write_work_dir(plan: PlanInput, photos: dict[str, bytes], work_dir: Path) -> None:
    """作業ディレクトリを作り直し、``photos/`` と ``photos.json`` を置く（前回の出力は消す）。"""
    if work_dir.exists():
        shutil.rmtree(work_dir)
    (work_dir / "photos").mkdir(parents=True)
    for image, data in photos.items():
        (work_dir / image).write_bytes(data)
    (work_dir / PHOTOS_JSON).write_text(plan.model_dump_json(indent=2), encoding="utf-8")

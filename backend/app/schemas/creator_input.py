"""作成入力の中間データ ``photos.json``（PlanInput）。

作る人が撮った写真列（画像 + 座標、撮った順）と出発地・目的地・命名をまとめたもの。
フロントから受けても CLI で作っても同じ形にし、以降の処理はこのファイルだけを入口にする。
契約: docs/interface.md 4 章。画像は ``photos/<id>.jpg`` に置く。
"""
from __future__ import annotations

import re
from typing import Literal

from pydantic import BaseModel, Field, model_validator

LocationSource = Literal["gps", "manual", "exif"]
PHOTO_IMAGE_PATTERN = re.compile(r"^photos/[A-Za-z0-9_-]+\.(jpg|jpeg|png)$")


class PlaceInput(BaseModel):
    """地名だけ、または地名 + 座標（「現在地から」用）。"""

    query: str = Field(min_length=1)
    lat: float | None = Field(default=None, ge=-90, le=90)
    lng: float | None = Field(default=None, ge=-180, le=180)

    @model_validator(mode="after")
    def _both_or_none(self) -> "PlaceInput":
        if (self.lat is None) != (self.lng is None):
            raise ValueError("lat と lng は両方書くか両方省く")
        return self


class CreatorPhoto(BaseModel):
    id: str = Field(pattern=r"^[A-Za-z0-9_-]{1,64}$")
    seq: int = Field(ge=0)  # 撮影順。配列順と一致
    image: str = Field(pattern=PHOTO_IMAGE_PATTERN.pattern)  # photos/<id>.jpg（入力ディレクトリからの相対）
    lat: float = Field(ge=-90, le=90)
    lng: float = Field(ge=-180, le=180)
    accuracy_m: float | None = Field(default=None, ge=0)  # Geolocation の accuracy
    taken_at: str | None = None  # ISO 8601
    location_source: LocationSource = "gps"
    caption: str | None = None  # あれば目印文にそのまま使い、VLM は呼ばない


class PlanOptions(BaseModel):
    use_vlm_on_photos: bool = False  # 写真地点で VLM・矢印を行うか（既定: 行わない）


class PlanInput(BaseModel):
    version: Literal[1] = 1
    name: str = Field(min_length=1)  # 命名（保存キー）
    origin: PlaceInput
    destination: PlaceInput
    creator_id: str | None = None
    created_at: str | None = None
    photos: list[CreatorPhoto] = Field(default_factory=list)
    options: PlanOptions = Field(default_factory=PlanOptions)

    @model_validator(mode="before")
    @classmethod
    def _coerce_places(cls, data: object) -> object:
        """origin / destination は文字列だけでも書ける。"""
        if isinstance(data, dict):
            data = dict(data)
            for k in ("origin", "destination"):
                if isinstance(data.get(k), str):
                    data[k] = {"query": data[k]}
        return data

    @model_validator(mode="after")
    def _check_photos(self) -> "PlanInput":
        seqs = [p.seq for p in self.photos]
        if seqs != list(range(len(seqs))):
            raise ValueError(f"photos[].seq は 0 から連続で配列順と一致させる: {seqs}")
        ids = [p.id for p in self.photos]
        if len(set(ids)) != len(ids):
            raise ValueError("photos[].id が重複している")
        if self.name.strip() == "":
            raise ValueError("name が空")
        return self

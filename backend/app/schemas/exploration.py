"""経路探索の中間形式 ``route.json``。

バックエンド内部でのみ使う。仕様: docs/route-exploration.md
後続ステップ（VLM・矢印描画）は ``landmark`` と ``arrow_image`` を埋めて上書き保存する。
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

Turn = Literal["left", "right", "straight", "arrive"]
ImageSource = Literal["street_view", "creator_photo"]


class Place(BaseModel):
    query: str
    lat: float
    lng: float


class StreetViewMeta(BaseModel):
    pano_id: str
    date: str | None = None
    heading: float
    fov: int = 90
    pitch: int = 0


class ExplorationPoint(BaseModel):
    index: int
    lat: float
    lng: float
    heading: float | None = Field(default=None, ge=0, lt=360)  # 交差点に近づく向き（出発点は出て行く向き）
    maneuver: str
    turn: Turn
    instruction: str
    distance_to_next_m: int = Field(ge=0)
    image: str | None = None
    image_source: ImageSource | None = None
    street_view: StreetViewMeta | None = None
    landmark: str | None = None
    arrow_image: str | None = None


class Exploration(BaseModel):
    version: Literal[1] = 1
    origin: Place
    destination: Place
    polyline: str
    total_distance_m: int = Field(ge=0)
    points: list[ExplorationPoint]

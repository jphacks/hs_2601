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
    copyright: str | None = None  # "© 2026 Google" なら公式撮影。それ以外はユーザー投稿
    offset_m: float = 0.0  # 交差点の何 m 手前のパノラマを使ったか


class ArrowPoint(BaseModel):
    """画像内の座標。左上 (0,0)、右下 (1,1)。"""

    x: float = Field(ge=0, le=1)
    y: float = Field(ge=0, le=1)


class VlmScore(BaseModel):
    landmark: int = Field(ge=1, le=5)  # 目印のわかりやすさ
    turn: int = Field(ge=1, le=5)  # どこで曲がるかのわかりやすさ
    arrow: int = Field(default=3, ge=1, le=5)  # 矢印の描きやすさ・わかりやすさ（曲がる先の路面が見えているか）
    view: int = Field(default=3, ge=1, le=5)  # 人の視点に近いか（現在は評価軸から外している）
    landmark_text: str = ""  # この画像での目印の短い説明
    reason: str = ""
    arrow_path: list[ArrowPoint] = Field(default_factory=list)  # 歩行者の足元から曲がる先の路面までの経路（3〜6 点）


class ImageCandidate(BaseModel):
    """1 地点に対する Street View の候補画像。向き・位置の違いで複数作る。"""

    image: str  # out/ からの相対パス
    heading_mode: str  # approach / bisector / departure
    street_view: StreetViewMeta
    score: VlmScore | None = None  # ステップ 7 で埋まる


class ExplorationPoint(BaseModel):
    index: int
    lat: float
    lng: float
    heading: float | None = Field(default=None, ge=0, lt=360)  # 交差点に近づく向き（出発点は出て行く向き）
    heading_out: float | None = Field(default=None, ge=0, lt=360)  # 交差点から出て行く向き（目的地は null）
    maneuver: str
    turn: Turn
    instruction: str
    distance_to_next_m: int = Field(ge=0)
    image: str | None = None  # 採用した画像。候補があるときは chosen_candidate の image と同じ
    image_source: ImageSource | None = None
    street_view: StreetViewMeta | None = None
    candidates: list[ImageCandidate] = Field(default_factory=list)  # ステップ 5 で複数取得
    chosen_candidate: int | None = None  # ステップ 7 で VLM が選んだ候補の番号
    landmark: str | None = None
    arrow_image: str | None = None


class Exploration(BaseModel):
    version: Literal[1] = 1
    origin: Place
    destination: Place
    polyline: str
    total_distance_m: int = Field(ge=0)
    points: list[ExplorationPoint]

"""参加者に渡す写真列 JSON（公開形式）。DB の ``route_plans.plan_json`` に入る。

中間形式 ``Exploration``（route.json）から候補画像や VLM の採点を落とし、
画像は公開 URL にしたもの。仕様: docs/follower.md「道案内取得 API」
"""
from __future__ import annotations

import hashlib
import re
from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.exploration import Turn

PlanStatus = Literal["draft", "published"]
PLAN_ID_LENGTH = 12
PLAN_ID_PATTERN = re.compile(r"[A-Za-z0-9_-]{1,64}")  # URL とストレージのパスにそのまま使える文字だけ


def validate_plan_id(plan_id: str) -> str:
    if not PLAN_ID_PATTERN.fullmatch(plan_id):
        raise ValueError(f"公開 ID は英数字・-・_ の 1〜64 文字にしてください: {plan_id!r}")
    return plan_id


def plan_id_for(name: str) -> str:
    """命名から公開 ID を作る。同じ名前なら同じ ID（保存し直すと上書き）。"""
    return hashlib.sha256(name.strip().encode("utf-8")).hexdigest()[:PLAN_ID_LENGTH]


class RouteStep(BaseModel):
    index: int
    lat: float
    lng: float
    turn: Turn
    instruction: str
    landmark: str | None = None
    distance_to_next_m: int = Field(ge=0)
    image_url: str | None = None  # 矢印入り画像の公開 URL。画像が無い地点は null


class RoutePlan(BaseModel):
    version: Literal[1] = 1
    origin: str
    destination: str
    polyline: str
    total_distance_m: int = Field(ge=0)
    steps: list[RouteStep]


class RoutePlanRecord(BaseModel):
    """DB の 1 行。"""

    id: str
    name: str
    status: PlanStatus = "published"
    origin: str
    destination: str
    plan: RoutePlan

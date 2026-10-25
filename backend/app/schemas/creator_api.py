"""作る人の HTTP API の入出力（docs/interface.md 5 章）。

JSON のキーは camelCase（フロントの frontend/src/shared/types/creator.ts と 1:1）。
Python 側は snake_case で書き、``alias_generator`` で camelCase に出す。
詳細取得の ``RoutePlanRecord`` だけは 1 章どおり snake_case のまま（route_plan.py）。
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel

from app.schemas.route_plan import PlanStatus

JobState = Literal["running", "done", "failed"]
JobStep = Literal["geocode", "route", "streetview", "landmark", "arrow", "save"]


class CamelModel(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, frozen=True)


class CreateRouteResponse(CamelModel):
    """POST /api/routes（202）"""

    job_id: str
    route_id: str


class JobStatus(CamelModel):
    """GET /api/jobs/{jobId}。``route_id`` は受付時から入る。``message`` は失敗時だけ（利用者向けの日本語）。"""

    job_id: str
    state: JobState
    step: JobStep | None = None
    route_id: str | None = None
    message: str | None = None


class RouteSummary(CamelModel):
    """GET /api/routes?creator_id=... の 1 件。"""

    id: str
    name: str
    origin: str
    destination: str
    status: PlanStatus
    created_at: str | None = None


class PublishResponse(CamelModel):
    """POST /api/routes/{id}/publish"""

    route_id: str
    url: str
    qr_path: str

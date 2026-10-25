"""永続化のインターフェース。Supabase とローカル実装を差し替えられるようにする。"""
from __future__ import annotations

from typing import Protocol

from app.schemas.route_plan import PlanStatus, RoutePlan, RoutePlanRecord, RoutePlanSummary


class RoutePlanRepository(Protocol):
    def save(self, record: RoutePlanRecord) -> RoutePlanRecord:
        """同じ id があれば上書きし、保存後のレコードを返す。"""
        ...

    def get_by_id(self, plan_id: str) -> RoutePlanRecord | None: ...

    def get_by_name(self, name: str) -> RoutePlanRecord | None: ...

    def list_by_creator(self, creator_id: str) -> list[RoutePlanSummary]:
        """作成者の道案内を新しい順に返す。"""
        ...

    def set_status(self, plan_id: str, status: PlanStatus) -> RoutePlanRecord | None:
        """status だけを変える。行が無ければ None。"""
        ...

    def update_plan(self, plan_id: str, plan: RoutePlan, expected_status: PlanStatus) -> RoutePlanRecord | None:
        """status が expected_status の行だけ plan を書き換える（status は変えない）。合わなければ None。"""
        ...


class PhotoStorage(Protocol):
    def put(self, path: str, data: bytes, content_type: str) -> str:
        """保存して公開 URL を返す。"""
        ...

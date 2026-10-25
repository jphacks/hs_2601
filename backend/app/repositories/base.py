"""永続化のインターフェース。Supabase とローカル実装を差し替えられるようにする。"""
from __future__ import annotations

from typing import Protocol

from app.schemas.route_plan import RoutePlanRecord


class RoutePlanRepository(Protocol):
    def save(self, record: RoutePlanRecord) -> RoutePlanRecord:
        """同じ id があれば上書きし、保存後のレコードを返す。"""
        ...

    def get_by_id(self, plan_id: str) -> RoutePlanRecord | None: ...

    def get_by_name(self, name: str) -> RoutePlanRecord | None: ...


class PhotoStorage(Protocol):
    def put(self, path: str, data: bytes, content_type: str) -> str:
        """保存して公開 URL を返す。"""
        ...

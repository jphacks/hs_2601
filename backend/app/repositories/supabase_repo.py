"""Supabase 実装。テーブル ``route_plans`` と公開バケット ``plans``（supabase/migrations 参照）。"""
from __future__ import annotations

from typing import Any

from app.external.supabase.rest import SupabaseRest
from app.schemas.route_plan import PlanStatus, RoutePlan, RoutePlanRecord, RoutePlanSummary

TABLE = "route_plans"
BUCKET = "plans"
SUMMARY_COLUMNS = "id,name,status,origin,destination,created_at"


def record_to_row(r: RoutePlanRecord) -> dict[str, Any]:
    row = {"id": r.id, "name": r.name, "status": r.status, "origin": r.origin, "destination": r.destination,
           "plan_json": r.plan.model_dump(mode="json")}
    # creator_id 列はマイグレーション 20261025120000 で足した。None のときは送らない
    # （列がまだ無い DB でも CLI の保存が通るように。upsert は送った列だけ上書きする）
    return {**row, "creator_id": r.creator_id} if r.creator_id is not None else row


def row_to_record(row: dict[str, Any]) -> RoutePlanRecord:
    return RoutePlanRecord(id=row["id"], name=row["name"], status=row["status"], origin=row["origin"],
                           destination=row["destination"], plan=RoutePlan.model_validate(row["plan_json"]),
                           creator_id=row.get("creator_id"))


def row_to_summary(row: dict[str, Any]) -> RoutePlanSummary:
    return RoutePlanSummary(id=row["id"], name=row["name"], status=row["status"], origin=row["origin"],
                            destination=row["destination"], created_at=row.get("created_at"))


class SupabaseRoutePlanRepository:
    def __init__(self, rest: SupabaseRest) -> None:
        self._rest = rest

    def save(self, record: RoutePlanRecord) -> RoutePlanRecord:
        rows = self._rest.upsert(TABLE, [record_to_row(record)], on_conflict="id")
        return row_to_record(rows[0]) if rows else record

    def get_by_id(self, plan_id: str) -> RoutePlanRecord | None:
        rows = self._rest.select(TABLE, {"id": f"eq.{plan_id}"})
        return row_to_record(rows[0]) if rows else None

    def get_by_name(self, name: str) -> RoutePlanRecord | None:
        rows = self._rest.select(TABLE, {"name": f"eq.{name.strip()}"})
        return row_to_record(rows[0]) if rows else None

    def list_by_creator(self, creator_id: str) -> list[RoutePlanSummary]:
        rows = self._rest.select(TABLE, {"creator_id": f"eq.{creator_id}", "order": "created_at.desc"}, columns=SUMMARY_COLUMNS)
        return [row_to_summary(r) for r in rows]

    def set_status(self, plan_id: str, status: PlanStatus) -> RoutePlanRecord | None:
        rows = self._rest.update(TABLE, {"id": f"eq.{plan_id}"}, {"status": status})
        return row_to_record(rows[0]) if rows else None


class SupabasePhotoStorage:
    def __init__(self, rest: SupabaseRest, bucket: str = BUCKET) -> None:
        self._rest = rest
        self._bucket = bucket

    def put(self, path: str, data: bytes, content_type: str) -> str:
        return self._rest.upload(self._bucket, path, data, content_type, upsert=True)

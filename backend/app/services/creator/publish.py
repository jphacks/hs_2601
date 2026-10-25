"""ステップ 9: 出力ディレクトリの写真列を、命名をキーにして DB とストレージへ保存する。

- 公開 ID は命名の SHA-256 先頭 12 桁（``plan_id_for``）。同じ名前なら同じ ID で上書きされる。
- 画像は矢印入り（``arrow_image``）を優先し、無ければ採用画像（``image``）。``plans/{id}/NNN.jpg`` に置く。
- 元の Exploration は変更しない。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from app.repositories.base import PhotoStorage, RoutePlanRepository
from app.schemas.exploration import Exploration, ExplorationPoint
from app.schemas.route_plan import RoutePlan, RoutePlanRecord, RouteStep, plan_id_for, validate_plan_id

CONTENT_TYPES = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png"}


@dataclass(frozen=True)
class PublishResult:
    record: RoutePlanRecord
    uploaded: list[int] = field(default_factory=list)  # 画像を上げた地点
    skipped: list[int] = field(default_factory=list)  # 画像が無かった地点


def image_for(p: ExplorationPoint) -> str | None:
    return p.arrow_image or p.image


def storage_path(plan_id: str, p: ExplorationPoint, src: Path) -> str:
    return f"{plan_id}/{p.index:03d}{src.suffix.lower()}"


def upload_point_image(storage: PhotoStorage, plan_id: str, p: ExplorationPoint, out_dir: Path) -> str | None:
    rel = image_for(p)
    if not rel:
        return None
    src = (out_dir / rel).resolve()
    if not src.is_relative_to(out_dir.resolve()):  # route.json の画像パスは出力ディレクトリ内に限る
        raise ValueError(f"地点 {p.index}: 画像パスが出力ディレクトリの外を指しています: {rel}")
    content_type = CONTENT_TYPES.get(src.suffix.lower())
    if content_type is None:
        raise ValueError(f"地点 {p.index}: 対応していない画像形式です: {rel}")
    return storage.put(storage_path(plan_id, p, src), src.read_bytes(), content_type)


def to_step(p: ExplorationPoint, image_url: str | None) -> RouteStep:
    return RouteStep(index=p.index, lat=p.lat, lng=p.lng, turn=p.turn, instruction=p.instruction,
                     landmark=p.landmark, distance_to_next_m=p.distance_to_next_m, image_url=image_url)


def publish_plan(
    e: Exploration, out_dir: Path, name: str, repo: RoutePlanRepository, storage: PhotoStorage, *, plan_id: str | None = None
) -> PublishResult:
    name = name.strip()
    if not name:
        raise ValueError("命名（--name）が空です。")
    pid = validate_plan_id(plan_id or plan_id_for(name))
    existing = repo.get_by_name(name)
    if existing is not None and existing.id != pid:  # name は UNIQUE。画像を上げる前に気づく
        raise ValueError(f"命名 {name!r} は既に id={existing.id} で保存されています。同じ名前で上書きするなら --id を外してください。")
    uploaded: list[int] = []
    skipped: list[int] = []
    steps: list[RouteStep] = []
    for p in e.points:
        url = upload_point_image(storage, pid, p, out_dir)
        (uploaded if url else skipped).append(p.index)
        steps.append(to_step(p, url))
    plan = RoutePlan(origin=e.origin.query, destination=e.destination.query, polyline=e.polyline,
                     total_distance_m=e.total_distance_m, steps=steps)
    record = repo.save(RoutePlanRecord(id=pid, name=name, origin=e.origin.query, destination=e.destination.query, plan=plan))
    return PublishResult(record, uploaded, skipped)

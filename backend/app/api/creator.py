"""作る人（creator）向け API。契約: docs/interface.md 5 章。

- POST /api/routes                 作成受付（multipart: manifest + photos）。202 {jobId, routeId}
- GET  /api/jobs/{jobId}           進み具合
- GET  /api/routes?creator_id=...  作成者の一覧（新しい順）
- GET  /api/routes/{id}            詳細（下書きも返す）
- POST /api/routes/{id}/publish    公開。{routeId, url, qrPath}
- GET  /api/routes/{id}/qr.png     参加者 URL の QR
作成はバックグラウンドで走り、終わると route_plans に status = "draft" で保存される。
"""
from __future__ import annotations

import logging
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import Response

from app.api.deps import (
    get_admin_repo, get_job_store, get_photo_storage, get_pipeline_runner, get_public_base_url, get_work_root,
)
from app.external.supabase.rest import SupabaseError
from app.imaging.qr import qr_png
from app.repositories.base import PhotoStorage, RoutePlanRepository
from app.schemas.creator_api import CreateRouteResponse, JobStatus, PublishResponse, RouteSummary
from app.schemas.creator_input import PlanInput
from app.schemas.route_plan import RoutePlanRecord, plan_id_for, validate_plan_id
from app.services.creator.creation import CreationJob, PipelineRunner, run_creation_job
from app.services.creator.intake import (
    MAX_PHOTO_BYTES, UploadedPhoto, match_photos, normalize_photos, parse_manifest, write_work_dir,
)
from app.services.creator.jobs import JobStore
from app.services.creator.photos import PlanInputError
from app.services.follower.fetch import participant_url

log = logging.getLogger(__name__)
router = APIRouter()


@contextmanager
def supabase_errors() -> Iterator[None]:
    """保存先との通信失敗は 502。詳細はログだけに残す。"""
    try:
        yield
    except SupabaseError as e:
        log.exception("supabase error: %s", e)
        raise HTTPException(502, "保存先との通信に失敗しました。しばらくしてから試してください。") from e


def _route_id(plan_id: str) -> str:
    try:
        return validate_plan_id(plan_id)
    except ValueError as e:
        raise HTTPException(404, "不正な ID です。") from e


def _read_uploads(files: list[UploadFile]) -> list[UploadedPhoto]:
    # 上限 + 1 バイトまで読み、超えたものは match_photos が 400 にする
    return [UploadedPhoto(f.filename or "", f.file.read(MAX_PHOTO_BYTES + 1)) for f in files]


def _check_owner(plan: PlanInput, route_id: str, repo: RoutePlanRepository) -> None:
    with supabase_errors():
        existing = repo.get_by_id(route_id)
    if existing is not None and existing.creator_id != plan.creator_id:
        raise HTTPException(409, "同じ名前の道案内が既にあります。別の名前にしてください。")


@router.post("/routes", status_code=202, response_model=CreateRouteResponse)
def create_route(
    background: BackgroundTasks,
    manifest: str | None = Form(None),
    photos: list[UploadFile] | None = File(None),
    repo: RoutePlanRepository = Depends(get_admin_repo),
    storage: PhotoStorage = Depends(get_photo_storage),
    pipeline: PipelineRunner = Depends(get_pipeline_runner),
    store: JobStore = Depends(get_job_store),
    work_root: Path = Depends(get_work_root),
) -> CreateRouteResponse:
    try:
        plan = parse_manifest(manifest)
        matched = match_photos(plan, _read_uploads(photos or []))
    except PlanInputError as e:
        raise HTTPException(400, str(e)) from e
    route_id = plan_id_for(plan.name)
    _check_owner(plan, route_id, repo)
    try:
        normalized = normalize_photos(matched)
    except PlanInputError as e:
        raise HTTPException(400, str(e)) from e
    job = store.start(route_id)
    if job is None:
        raise HTTPException(409, "同じ名前の道案内を作成中です。終わるまで待ってください。")
    work_dir = work_root / route_id
    write_work_dir(plan, normalized, work_dir)
    background.add_task(run_creation_job, CreationJob(job.job_id, route_id, plan, work_dir), store, pipeline, repo, storage)
    return CreateRouteResponse(job_id=job.job_id, route_id=route_id)


@router.get("/jobs/{job_id}", response_model=JobStatus)
def get_job(job_id: str, store: JobStore = Depends(get_job_store)) -> JobStatus:
    job = store.get(job_id)
    if job is None:
        raise HTTPException(404, "ジョブが見つかりません（サーバーが再起動した可能性があります）。")
    return job


@router.get("/routes", response_model=list[RouteSummary])
def list_routes(creator_id: str | None = Query(None), repo: RoutePlanRepository = Depends(get_admin_repo)) -> list[RouteSummary]:
    if not creator_id or not creator_id.strip():
        raise HTTPException(400, "creator_id を指定してください。")
    with supabase_errors():
        rows = repo.list_by_creator(creator_id.strip())
    return [RouteSummary(id=r.id, name=r.name, origin=r.origin, destination=r.destination, status=r.status,
                         created_at=r.created_at) for r in rows]


def _load(plan_id: str, repo: RoutePlanRepository) -> RoutePlanRecord:
    pid = _route_id(plan_id)
    with supabase_errors():
        rec = repo.get_by_id(pid)
    if rec is None:
        raise HTTPException(404, "道案内が見つかりません。")
    return rec


@router.get("/routes/{plan_id}", response_model=RoutePlanRecord)
def get_route(plan_id: str, repo: RoutePlanRepository = Depends(get_admin_repo)) -> RoutePlanRecord:
    return _load(plan_id, repo)


@router.post("/routes/{plan_id}/publish", response_model=PublishResponse)
def publish_route(plan_id: str, repo: RoutePlanRepository = Depends(get_admin_repo),
                  base_url: str = Depends(get_public_base_url)) -> PublishResponse:
    pid = _route_id(plan_id)
    with supabase_errors():
        rec = repo.set_status(pid, "published")
    if rec is None:
        raise HTTPException(404, "道案内が見つかりません。")
    return PublishResponse(route_id=pid, url=participant_url(base_url, pid), qr_path=f"/api/routes/{pid}/qr.png")


@router.get("/routes/{plan_id}/qr.png", response_class=Response)
def route_qr(plan_id: str, repo: RoutePlanRepository = Depends(get_admin_repo),
             base_url: str = Depends(get_public_base_url)) -> Response:
    rec = _load(plan_id, repo)
    return Response(content=qr_png(participant_url(base_url, rec.id)), media_type="image/png")

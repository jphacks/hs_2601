"""API の依存関係。テストでは app.dependency_overrides で差し替える。"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from fastapi import HTTPException, Request

from app.core.config import get_settings
from app.external.supabase.rest import SupabaseRest
from app.repositories.base import PhotoStorage, RoutePlanRepository
from app.repositories.supabase_repo import SupabasePhotoStorage, SupabaseRoutePlanRepository
from app.services.creator.creation import PipelineRunner
from app.services.creator.jobs import JobStore
from app.services.creator.pipeline import PhotoPipeline, make_clients

WORK_SUBDIR = "routes"  # 作成受付の作業ディレクトリ: {out_dir}/routes/<routeId>/


@lru_cache
def get_public_repo() -> RoutePlanRepository:
    """参加者向け。anon キーで読むので、公開済みの行しか見えない（RLS）。"""
    s = get_settings()
    if not s.supabase_url or not s.supabase_anon_key:
        raise HTTPException(503, "SUPABASE_URL / SUPABASE_ANON_KEY が未設定です。")
    return SupabaseRoutePlanRepository(SupabaseRest(s.supabase_url, s.supabase_anon_key))


@lru_cache
def _admin_rest() -> SupabaseRest:
    try:
        return SupabaseRest(*get_settings().require_supabase())
    except RuntimeError as e:
        raise HTTPException(503, "SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY が未設定です。") from e


def get_admin_repo() -> RoutePlanRepository:
    """作る人向け。service_role キーで読み書きするので、下書きも見える。"""
    return SupabaseRoutePlanRepository(_admin_rest())


def get_photo_storage() -> PhotoStorage:
    return SupabasePhotoStorage(_admin_rest())


@lru_cache
def get_job_store() -> JobStore:
    """プロセスに 1 つ。再起動で消える。"""
    return JobStore()


def get_pipeline_runner() -> PipelineRunner:
    s = get_settings()
    if not s.google_maps_api_key:
        raise HTTPException(503, "GOOGLE_MAPS_API_KEY が未設定です。")
    return PhotoPipeline(make_clients=lambda: make_clients(s))


def get_work_root() -> Path:
    return get_settings().out_dir / WORK_SUBDIR


def get_public_base_url(request: Request) -> str:
    """参加者 URL の土台。PUBLIC_BASE_URL が無ければこのサーバー自身（/r/{id} の HTML がある）。"""
    return get_settings().public_base_url or str(request.base_url)

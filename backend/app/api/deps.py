"""API の依存関係。テストでは app.dependency_overrides で差し替える。"""
from __future__ import annotations

from functools import lru_cache

from fastapi import HTTPException

from app.core.config import get_settings
from app.external.supabase.rest import SupabaseRest
from app.repositories.base import RoutePlanRepository
from app.repositories.supabase_repo import SupabaseRoutePlanRepository


@lru_cache
def get_public_repo() -> RoutePlanRepository:
    """参加者向け。anon キーで読むので、公開済みの行しか見えない（RLS）。"""
    s = get_settings()
    if not s.supabase_url or not s.supabase_anon_key:
        raise HTTPException(503, "SUPABASE_URL / SUPABASE_ANON_KEY が未設定です。")
    return SupabaseRoutePlanRepository(SupabaseRest(s.supabase_url, s.supabase_anon_key))

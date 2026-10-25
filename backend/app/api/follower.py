"""参加者（follower）向け API。

- GET /api/public/routes/{id}  公開済みの写真列（JSON、RoutePlanRecord）。フロント用
- GET /r/{id}                  同じものを HTML で表示。フロントが無くてもスマホで見られる（QR の飛び先）
仕様: docs/follower.md、契約: docs/interface.md
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import HTMLResponse

from app.api.deps import get_public_repo
from app.repositories.base import RoutePlanRepository
from app.schemas.route_plan import PLAN_ID_PATTERN, RoutePlanRecord
from app.services.follower.fetch import fetch_plan
from app.services.follower.view import render_plan_html

router = APIRouter()
pages = APIRouter()  # prefix 無し（/r/{id}）


def _load(plan_id: str, repo: RoutePlanRepository) -> RoutePlanRecord:
    if not PLAN_ID_PATTERN.fullmatch(plan_id):
        raise HTTPException(404, "不正な ID です。")
    rec = fetch_plan(repo, plan_id)
    if rec is None:
        raise HTTPException(404, "道案内が見つかりません（未保存か未公開）。")
    return rec


@router.get("/public/routes/{plan_id}", response_model=RoutePlanRecord)
def get_public_route(plan_id: str, repo: RoutePlanRepository = Depends(get_public_repo)) -> RoutePlanRecord:
    return _load(plan_id, repo)


@pages.get("/r/{plan_id}", response_class=HTMLResponse)
def participant_page(plan_id: str, repo: RoutePlanRepository = Depends(get_public_repo)) -> str:
    return render_plan_html(_load(plan_id, repo))

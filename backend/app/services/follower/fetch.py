"""参加者側: QR の URL から公開 ID を取り出し、写真列を取得する。

契約は docs/interface.md。URL は {PUBLIC_BASE_URL}/r/<id>、取得は Supabase の route_plans を anon キーで読む。
"""
from __future__ import annotations

import re
from urllib.parse import urlsplit

from app.repositories.base import RoutePlanRepository
from app.schemas.route_plan import PLAN_ID_PATTERN, RoutePlanRecord

PARTICIPANT_PATH = re.compile(r"^/r/(?P<id>[^/]+)/?$")


def participant_url(base_url: str, plan_id: str) -> str:
    return f"{base_url.rstrip('/')}/r/{plan_id}"


def plan_id_from_url(url: str) -> str:
    """参加者 URL（QR の中身）から公開 ID を取り出す。形が違えば ValueError。"""
    m = PARTICIPANT_PATH.match(urlsplit(url).path)
    if not m or not PLAN_ID_PATTERN.fullmatch(m["id"]):
        raise ValueError(f"参加者 URL ではありません（{{base}}/r/<id> の形が必要）: {url}")
    return m["id"]


def fetch_plan(repo: RoutePlanRepository, plan_id: str) -> RoutePlanRecord | None:
    """公開済みの写真列を返す。無ければ None（未保存か、未公開で RLS に隠されている）。"""
    return repo.get_by_id(plan_id)

"""作る人 API 用に足した Supabase の操作（creator_id・一覧・status 変更）を、HTTP をモックして確かめる。"""
import json

import httpx

from app.external.supabase.rest import SupabaseRest
from app.repositories.supabase_repo import SupabaseRoutePlanRepository, record_to_row
from tests.test_follower_api import record

URL = "https://proj.supabase.co"


def repo(handler) -> SupabaseRoutePlanRepository:
    return SupabaseRoutePlanRepository(SupabaseRest(URL, "svc", http=httpx.Client(transport=httpx.MockTransport(handler))))


def row(**kw) -> dict:
    return {**record_to_row(record()), **kw}


def test_creator_idがNoneなら列を送らない_あれば送る() -> None:
    assert "creator_id" not in record_to_row(record())
    assert record_to_row(record().model_copy(update={"creator_id": "c1"}))["creator_id"] == "c1"


def test_作成者で絞り_新しい順の一覧を取る() -> None:
    def handler(req: httpx.Request) -> httpx.Response:
        p = req.url.params
        assert req.method == "GET" and p["creator_id"] == "eq.c1" and p["order"] == "created_at.desc"
        assert "plan_json" not in p["select"] and "created_at" in p["select"]
        return httpx.Response(200, json=[{"id": "b", "name": "B", "status": "draft", "origin": "o", "destination": "d",
                                          "created_at": "2026-10-25T10:00:00+00:00"}])

    rows = repo(handler).list_by_creator("c1")
    assert [(r.id, r.status, r.created_at) for r in rows] == [("b", "draft", "2026-10-25T10:00:00+00:00")]


def test_status変更はPATCHで_行が無ければNone() -> None:
    seen: list[httpx.Request] = []

    def handler(req: httpx.Request) -> httpx.Response:
        seen.append(req)
        if req.url.params["id"] == "eq.none":
            return httpx.Response(200, json=[])
        return httpx.Response(200, json=[row(status="published", creator_id="c1")])

    rec = repo(handler).set_status("abc123", "published")
    assert rec is not None and rec.status == "published" and rec.creator_id == "c1"
    assert seen[0].method == "PATCH" and json.loads(seen[0].content) == {"status": "published"}
    assert "return=representation" in seen[0].headers["prefer"]
    assert repo(handler).set_status("none", "published") is None

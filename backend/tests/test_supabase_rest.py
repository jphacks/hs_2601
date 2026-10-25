"""Supabase REST クライアントを、HTTP をモックして確認する（キー不要）。"""
import json

import httpx
import pytest

from app.external.supabase.rest import SupabaseError, SupabaseRest

URL = "https://proj.supabase.co"


def make(handler) -> SupabaseRest:
    return SupabaseRest(URL + "/", "svc-key", http=httpx.Client(transport=httpx.MockTransport(handler)))


def test_upsert_は重複を上書きし保存後の行を返す() -> None:
    def handler(req: httpx.Request) -> httpx.Response:
        assert req.method == "POST" and req.url.path == "/rest/v1/route_plans"
        assert req.url.params["on_conflict"] == "id"
        assert req.headers["apikey"] == "svc-key" and req.headers["authorization"] == "Bearer svc-key"
        assert "merge-duplicates" in req.headers["prefer"] and "return=representation" in req.headers["prefer"]
        return httpx.Response(201, json=json.loads(req.content))

    rows = make(handler).upsert("route_plans", [{"id": "a", "name": "n"}])
    assert rows == [{"id": "a", "name": "n"}]


def test_select_はPostgRESTのフィルタをそのまま渡す() -> None:
    def handler(req: httpx.Request) -> httpx.Response:
        assert req.url.params["id"] == "eq.abc" and req.url.params["select"] == "*"
        return httpx.Response(200, json=[{"id": "abc"}])

    assert make(handler).select("route_plans", {"id": "eq.abc"}) == [{"id": "abc"}]


def test_upload_は上書きヘッダー付きで置き_公開URLを返す() -> None:
    def handler(req: httpx.Request) -> httpx.Response:
        assert req.url.path == "/storage/v1/object/plans/abc/000.jpg"
        assert req.headers["content-type"] == "image/jpeg" and req.headers["x-upsert"] == "true"
        assert req.content == b"img"
        return httpx.Response(200, json={"Key": "plans/abc/000.jpg"})

    url = make(handler).upload("plans", "abc/000.jpg", b"img", "image/jpeg")
    assert url == f"{URL}/storage/v1/object/public/plans/abc/000.jpg"


def test_HTTPエラーはメッセージ付きで伝わる() -> None:
    def handler(req: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json={"message": "Invalid API key"})

    with pytest.raises(SupabaseError, match="HTTP 401"):
        make(handler).select("route_plans", {})


def test_接続エラーもSupabaseErrorになる() -> None:
    def handler(req: httpx.Request) -> httpx.Response:
        raise httpx.ConnectTimeout("timeout")

    with pytest.raises(SupabaseError, match="ConnectTimeout"):
        make(handler).select("route_plans", {})


def test_upload_はパスをURLエンコードしキャッシュ無効ヘッダーを付ける() -> None:
    def handler(req: httpx.Request) -> httpx.Response:
        assert req.url.raw_path == b"/storage/v1/object/plans/abc/0%2300.jpg"
        assert req.headers["cache-control"] == "no-cache"
        return httpx.Response(200, json={})

    assert make(handler).upload("plans", "abc/0#00.jpg", b"x", "image/jpeg").endswith("/plans/abc/0%2300.jpg")

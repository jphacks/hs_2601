"""Supabase の REST クライアント（PostgREST と Storage）。SDK を入れず httpx で直接叩く。

- テーブル: ``{url}/rest/v1/{table}``（PostgREST）
- 画像:     ``{url}/storage/v1/object/{bucket}/{path}``
認証はどちらも ``apikey`` と ``Authorization: Bearer`` ヘッダー。service_role キーなら RLS を通らない。
API: https://supabase.com/docs/guides/api, https://supabase.com/docs/reference/javascript/storage-from-upload
"""
from __future__ import annotations

from typing import Any
from urllib.parse import quote

import httpx


class SupabaseError(RuntimeError):
    pass


# 上書き後に古い画像が CDN に残らないようにする（既定は 3600 秒キャッシュ）
UPLOAD_CACHE_CONTROL = "no-cache"


class SupabaseRest:
    def __init__(self, url: str, key: str, http: httpx.Client | None = None) -> None:
        self._url = url.rstrip("/")
        self._http = http or httpx.Client(timeout=60.0)
        self._headers = {"apikey": key, "Authorization": f"Bearer {key}"}

    # --- PostgREST ---

    def upsert(self, table: str, rows: list[dict[str, Any]], *, on_conflict: str = "id") -> list[dict[str, Any]]:
        """行を挿入し、キーが重複していれば上書きする。保存後の行を返す。"""
        res = self._request(
            "POST", f"{self._url}/rest/v1/{table}", f"upsert {table}",
            params={"on_conflict": on_conflict},
            headers={**self._headers, "Prefer": "resolution=merge-duplicates,return=representation"},
            json=rows,
        )
        return self._json(res, f"upsert {table}")

    def select(self, table: str, filters: dict[str, str], *, columns: str = "*") -> list[dict[str, Any]]:
        """``filters`` は PostgREST の書式（例: ``{"id": "eq.abc"}``）。"""
        res = self._request("GET", f"{self._url}/rest/v1/{table}", f"select {table}",
                            params={"select": columns, **filters}, headers=self._headers)
        return self._json(res, f"select {table}")

    def update(self, table: str, filters: dict[str, str], values: dict[str, Any]) -> list[dict[str, Any]]:
        """``filters`` に合う行の ``values`` の列だけを書き換え、更新後の行を返す（合う行が無ければ空）。"""
        res = self._request("PATCH", f"{self._url}/rest/v1/{table}", f"update {table}", params=filters,
                            headers={**self._headers, "Prefer": "return=representation"}, json=values)
        return self._json(res, f"update {table}")

    # --- Storage ---

    def upload(self, bucket: str, path: str, data: bytes, content_type: str, *, upsert: bool = True) -> str:
        """ファイルを置き、公開 URL を返す（バケットが公開設定であること）。"""
        res = self._request(
            "POST", f"{self._url}/storage/v1/object/{bucket}/{quote(path, safe='/')}", f"upload {bucket}/{path}",
            headers={**self._headers, "Content-Type": content_type, "x-upsert": "true" if upsert else "false",
                     "cache-control": UPLOAD_CACHE_CONTROL},
            content=data,
        )
        self._json(res, f"upload {bucket}/{path}")
        return self.public_url(bucket, path)

    def public_url(self, bucket: str, path: str) -> str:
        return f"{self._url}/storage/v1/object/public/{bucket}/{quote(path, safe='/')}"

    # --- 共通 ---

    def _request(self, method: str, url: str, what: str, **kw: Any) -> httpx.Response:
        try:
            return self._http.request(method, url, **kw)
        except httpx.HTTPError as e:  # タイムアウト・接続失敗も同じ例外型で伝える
            raise SupabaseError(f"Supabase {what} failed: {type(e).__name__}: {e}") from e

    @staticmethod
    def _json(res: httpx.Response, what: str) -> Any:
        if res.status_code >= 400:
            raise SupabaseError(f"Supabase {what} failed: HTTP {res.status_code} {res.text[:300]}")
        if not res.content:
            return []
        try:
            return res.json()
        except ValueError as e:
            raise SupabaseError(f"Supabase {what}: 返答が JSON ではありません: {res.text[:200]}") from e

"""Google Geocoding API クライアント。

住所・施設名の文字列を緯度経度に変換する。
API: https://developers.google.com/maps/documentation/geocoding
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import httpx

GEOCODING_URL = "https://maps.googleapis.com/maps/api/geocode/json"


class GeocodingError(RuntimeError):
    """API がエラー status を返した、または結果が 0 件だった。"""


@dataclass(frozen=True)
class GeocodeResult:
    query: str
    lat: float
    lng: float
    formatted_address: str
    place_id: str
    raw: dict[str, Any]


class GeocodingClient:
    def __init__(self, api_key: str, http: httpx.Client | None = None) -> None:
        self._api_key = api_key
        self._http = http or httpx.Client(timeout=10.0)

    def geocode(self, query: str, *, language: str = "ja", region: str = "jp") -> GeocodeResult:
        params = {"address": query, "key": self._api_key, "language": language, "region": region}
        res = self._http.get(GEOCODING_URL, params=params)
        res.raise_for_status()
        body: dict[str, Any] = res.json()
        return parse_geocode_response(query, body)


def parse_geocode_response(query: str, body: dict[str, Any]) -> GeocodeResult:
    """生レスポンスから先頭 1 件を取り出す。テストや fixture 再利用のため関数に分離。"""
    status = body.get("status")
    if status != "OK":
        detail = body.get("error_message", "")
        raise GeocodingError(f"Geocoding failed for {query!r}: status={status} {detail}".strip())
    results = body.get("results") or []
    if not results:
        raise GeocodingError(f"Geocoding returned no results for {query!r}")
    first = results[0]
    loc = first["geometry"]["location"]
    return GeocodeResult(
        query=query,
        lat=float(loc["lat"]),
        lng=float(loc["lng"]),
        formatted_address=first.get("formatted_address", ""),
        place_id=first.get("place_id", ""),
        raw=body,
    )

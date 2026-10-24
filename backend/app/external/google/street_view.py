"""Google Street View Static API クライアント。

- Metadata API: 指定地点の近くに画像があるかを返す（無料）
- Static API:   画像そのものを返す
API: https://developers.google.com/maps/documentation/streetview
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import httpx

METADATA_URL = "https://maps.googleapis.com/maps/api/streetview/metadata"
IMAGE_URL = "https://maps.googleapis.com/maps/api/streetview"

NO_IMAGE_STATUSES = {"ZERO_RESULTS", "NOT_FOUND"}


class StreetViewError(RuntimeError):
    """キーや権限の問題など、画像が無いこと以外の失敗。"""


@dataclass(frozen=True)
class PanoMeta:
    pano_id: str
    lat: float
    lng: float
    date: str | None  # "2023-05" など。無いこともある
    copyright: str
    raw: dict[str, Any]

    @property
    def is_official(self) -> bool:
        """Google 公式撮影か（ユーザー投稿は撮影者名が入る）。"""
        return "google" in self.copyright.lower()


class StreetViewClient:
    def __init__(self, api_key: str, http: httpx.Client | None = None) -> None:
        self._api_key = api_key
        self._http = http or httpx.Client(timeout=20.0)

    def metadata(self, lat: float, lng: float, *, radius_m: int = 50, outdoor_only: bool = True) -> PanoMeta | None:
        """近くに画像があればそのメタ情報、無ければ None。"""
        params: dict[str, Any] = {"location": f"{lat},{lng}", "radius": radius_m, "key": self._api_key}
        if outdoor_only:
            params["source"] = "outdoor"
        res = self._http.get(METADATA_URL, params=params)
        res.raise_for_status()
        return parse_metadata(res.json())

    def image(self, pano_id: str, *, heading: float, fov: int = 90, pitch: int = 0, size: str = "640x640") -> bytes:
        params = {"pano": pano_id, "heading": round(heading, 1), "fov": fov, "pitch": pitch, "size": size, "key": self._api_key}
        res = self._http.get(IMAGE_URL, params=params)
        if res.status_code != 200 or not res.headers.get("content-type", "").startswith("image/"):
            raise StreetViewError(f"Street View image failed: HTTP {res.status_code} {res.text[:200]}")
        return res.content


def parse_metadata(body: dict[str, Any]) -> PanoMeta | None:
    status = body.get("status")
    if status in NO_IMAGE_STATUSES:
        return None
    if status != "OK":
        raise StreetViewError(f"Street View metadata failed: status={status} {body.get('error_message', '')}".strip())
    loc = body.get("location", {})
    return PanoMeta(
        pano_id=body["pano_id"],
        lat=float(loc.get("lat", 0.0)),
        lng=float(loc.get("lng", 0.0)),
        date=body.get("date"),
        copyright=body.get("copyright", ""),
        raw=body,
    )

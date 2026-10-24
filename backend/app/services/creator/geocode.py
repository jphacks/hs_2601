"""ステップ 2: 出発地・目的地の文字列を座標にする。

external/google/geocoding.py を呼び、中間形式の Place に変換する。
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.external.google.geocoding import GeocodingClient, parse_geocode_response
from app.schemas.exploration import Place


@dataclass(frozen=True)
class GeocodeOutput:
    places: list[Place]
    raw: dict[str, Any]  # query → API 生レスポンス。raw/geocode.json に保存する


def geocode_queries(client: GeocodingClient, queries: list[str]) -> GeocodeOutput:
    places: list[Place] = []
    raw: dict[str, Any] = {}
    for q in queries:
        r = client.geocode(q)
        places.append(Place(query=q, lat=r.lat, lng=r.lng))
        raw[q] = r.raw
    return GeocodeOutput(places=places, raw=raw)


def geocode_from_raw(raw: dict[str, Any]) -> GeocodeOutput:
    """保存済みの raw/geocode.json から API を叩かずに復元する（--fixture 用）。"""
    places = [
        Place(query=q, lat=(r := parse_geocode_response(q, body)).lat, lng=r.lng)
        for q, body in raw.items()
    ]
    return GeocodeOutput(places=places, raw=raw)

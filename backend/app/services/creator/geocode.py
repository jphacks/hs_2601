"""ステップ 2: 出発地・目的地の文字列を座標にする。

external/google/geocoding.py を呼び、中間形式の Place に変換する。
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.external.google.geocoding import GeocodingClient, parse_geocode_response
from app.schemas.creator_input import PlaceInput
from app.schemas.exploration import Place
from app.services.creator.cache import FileCache, cache_key


@dataclass(frozen=True)
class GeocodeOutput:
    places: list[Place]
    raw: dict[str, Any]  # query → API 生レスポンス。raw/geocode.json に保存する


def geocode_queries(client: GeocodingClient, queries: list[str], cache: FileCache | None = None) -> GeocodeOutput:
    """地名ごとにキャッシュを引き、無ければ API を叩く。"""
    places: list[Place] = []
    raw: dict[str, Any] = {}
    for q in queries:
        key = cache_key("geocode", q)
        body = cache.get_json(key) if cache else None
        if body is None:
            body = client.geocode(q).raw
            if cache:
                cache.set_json(key, body)
        r = parse_geocode_response(q, body)
        places.append(Place(query=q, lat=r.lat, lng=r.lng))
        raw[q] = body
    return GeocodeOutput(places=places, raw=raw)


def geocode_from_raw(raw: dict[str, Any]) -> GeocodeOutput:
    """保存済みの raw/geocode.json から API を叩かずに復元する（--fixture 用）。"""
    places = [
        Place(query=q, lat=(r := parse_geocode_response(q, body)).lat, lng=r.lng)
        for q, body in raw.items()
    ]
    return GeocodeOutput(places=places, raw=raw)


def resolve_places(places: list[PlaceInput], client: GeocodingClient | None, cache: FileCache | None = None) -> list[Place]:
    """座標付きはそのまま、無ければ Geocoding。座標が全部あれば ``client`` は None でよい。"""
    need = [p.query for p in places if p.lat is None]
    found: dict[str, Place] = {}
    if need:
        if client is None:
            raise ValueError(f"座標の無い地名があるのに Geocoding クライアントがありません: {need}")
        found = {pl.query: pl for pl in geocode_queries(client, need, cache).places}
    return [Place(query=p.query, lat=p.lat, lng=p.lng) if p.lat is not None else found[p.query] for p in places]

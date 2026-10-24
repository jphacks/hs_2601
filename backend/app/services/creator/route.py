"""ステップ 3: 出発地・目的地（と経由地）から徒歩経路を取る。

external/google/routes.py を呼ぶ。経由地は作成者が写真を撮った地点で、順序最適化を有効にする。
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import polyline as polyline_codec

from app.external.google.routes import LatLng, Route, RoutesClient, parse_routes_response
from app.schemas.exploration import Place
from app.services.creator.cache import FileCache, cache_key


@dataclass(frozen=True)
class RouteOutput:
    route: Route
    raw: dict[str, Any]  # raw/routes.json に保存する


def compute_route(
    client: RoutesClient, origin: Place, destination: Place, via: list[Place] | None = None, cache: FileCache | None = None
) -> RouteOutput:
    """座標の組でキャッシュを引き、無ければ API を叩く。"""
    pts = [(origin.lat, origin.lng), *((p.lat, p.lng) for p in (via or [])), (destination.lat, destination.lng)]
    key = cache_key("routes", pts)
    body = cache.get_json(key) if cache else None
    if body is None:
        body = client.compute_walking_route(
            LatLng(origin.lat, origin.lng),
            LatLng(destination.lat, destination.lng),
            [LatLng(p.lat, p.lng) for p in (via or [])],
        ).raw
        if cache:
            cache.set_json(key, body)
    return RouteOutput(route=parse_routes_response(body), raw=body)


def route_from_raw(raw: dict[str, Any]) -> RouteOutput:
    """保存済みの raw/routes.json から API を叩かずに復元する。"""
    return RouteOutput(route=parse_routes_response(raw), raw=raw)


def decode_polyline(encoded: str) -> list[tuple[float, float]]:
    """エンコード済みポリライン → [(lat, lng), ...]"""
    if not encoded:
        return []
    return [(float(lat), float(lng)) for lat, lng in polyline_codec.decode(encoded)]

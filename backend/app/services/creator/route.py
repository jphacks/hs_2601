"""ステップ 3: 出発地・目的地（と経由地）から徒歩経路を取る。

external/google/routes.py を呼ぶ。経由地は作成者が写真を撮った地点で、順序最適化を有効にする。
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import polyline as polyline_codec

from app.external.google.routes import LatLng, Route, RoutesClient, parse_routes_response
from app.schemas.exploration import Place


@dataclass(frozen=True)
class RouteOutput:
    route: Route
    raw: dict[str, Any]  # raw/routes.json に保存する


def compute_route(client: RoutesClient, origin: Place, destination: Place, via: list[Place] | None = None) -> RouteOutput:
    route = client.compute_walking_route(
        LatLng(origin.lat, origin.lng),
        LatLng(destination.lat, destination.lng),
        [LatLng(p.lat, p.lng) for p in (via or [])],
    )
    return RouteOutput(route=route, raw=route.raw)


def route_from_raw(raw: dict[str, Any]) -> RouteOutput:
    """保存済みの raw/routes.json から API を叩かずに復元する。"""
    return RouteOutput(route=parse_routes_response(raw), raw=raw)


def decode_polyline(encoded: str) -> list[tuple[float, float]]:
    """エンコード済みポリライン → [(lat, lng), ...]"""
    if not encoded:
        return []
    return [(float(lat), float(lng)) for lat, lng in polyline_codec.decode(encoded)]

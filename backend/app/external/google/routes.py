"""Google Routes API クライアント（徒歩経路）。

API: https://developers.google.com/maps/documentation/routes
POST で呼び、キーは X-Goog-Api-Key ヘッダー、欲しい項目は X-Goog-FieldMask で指定する。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import httpx

ROUTES_URL = "https://routes.googleapis.com/directions/v2:computeRoutes"

FIELD_MASK = ",".join(
    [
        "routes.distanceMeters",
        "routes.duration",
        "routes.polyline.encodedPolyline",
        "routes.optimizedIntermediateWaypointIndex",
        "routes.legs.distanceMeters",
        "routes.legs.startLocation",
        "routes.legs.endLocation",
        "routes.legs.steps.distanceMeters",
        "routes.legs.steps.startLocation",
        "routes.legs.steps.endLocation",
        "routes.legs.steps.polyline.encodedPolyline",
        "routes.legs.steps.navigationInstruction",
    ]
)


class RoutesError(RuntimeError):
    """API がエラーを返した、または経路が 0 件だった。"""


@dataclass(frozen=True)
class LatLng:
    lat: float
    lng: float


@dataclass(frozen=True)
class RouteStep:
    start: LatLng
    end: LatLng
    distance_m: int
    maneuver: str  # Routes API の maneuver。無ければ "" 
    instruction: str  # 案内文。無ければ ""
    polyline: str


@dataclass(frozen=True)
class Route:
    distance_m: int
    duration_s: int
    polyline: str
    steps: list[RouteStep]
    optimized_waypoint_order: list[int] = field(default_factory=list)
    raw: dict[str, Any] = field(default_factory=dict)


def _loc(p: LatLng) -> dict[str, Any]:
    return {"location": {"latLng": {"latitude": p.lat, "longitude": p.lng}}}


def build_request_body(origin: LatLng, destination: LatLng, intermediates: list[LatLng], *, optimize: bool) -> dict[str, Any]:
    body: dict[str, Any] = {
        "origin": _loc(origin),
        "destination": _loc(destination),
        "travelMode": "WALK",
        "languageCode": "ja",
        "units": "METRIC",
    }
    if intermediates:
        body["intermediates"] = [_loc(p) for p in intermediates]
        if optimize and len(intermediates) >= 2:
            body["optimizeWaypointOrder"] = True
    return body


class RoutesClient:
    def __init__(self, api_key: str, http: httpx.Client | None = None) -> None:
        self._api_key = api_key
        self._http = http or httpx.Client(timeout=20.0)

    def compute_walking_route(
        self, origin: LatLng, destination: LatLng, intermediates: list[LatLng] | None = None, *, optimize: bool = True
    ) -> Route:
        body = build_request_body(origin, destination, intermediates or [], optimize=optimize)
        headers = {
            "Content-Type": "application/json",
            "X-Goog-Api-Key": self._api_key,
            "X-Goog-FieldMask": FIELD_MASK,
        }
        res = self._http.post(ROUTES_URL, json=body, headers=headers)
        if res.status_code != 200:
            raise RoutesError(f"Routes API failed: HTTP {res.status_code} {res.text[:300]}")
        return parse_routes_response(res.json())


def _latlng(d: dict[str, Any]) -> LatLng:
    ll = d["latLng"]
    return LatLng(lat=float(ll["latitude"]), lng=float(ll["longitude"]))


def parse_routes_response(body: dict[str, Any]) -> Route:
    """生レスポンスから先頭の経路を取り出す。fixture 再利用のため関数に分離。"""
    routes = body.get("routes") or []
    if not routes:
        raise RoutesError(f"Routes API returned no routes: {body}")
    r = routes[0]
    steps: list[RouteStep] = []
    for leg in r.get("legs", []):
        for s in leg.get("steps", []):
            nav = s.get("navigationInstruction") or {}
            steps.append(
                RouteStep(
                    start=_latlng(s["startLocation"]),
                    end=_latlng(s["endLocation"]),
                    distance_m=int(s.get("distanceMeters", 0)),
                    maneuver=nav.get("maneuver", ""),
                    instruction=nav.get("instructions", ""),
                    polyline=(s.get("polyline") or {}).get("encodedPolyline", ""),
                )
            )
    duration = r.get("duration", "0s")
    return Route(
        distance_m=int(r.get("distanceMeters", 0)),
        duration_s=int(float(str(duration).rstrip("s") or 0)),
        polyline=(r.get("polyline") or {}).get("encodedPolyline", ""),
        steps=steps,
        optimized_waypoint_order=list(r.get("optimizedIntermediateWaypointIndex", [])),
        raw=body,
    )

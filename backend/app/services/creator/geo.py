"""緯度経度の計算（純関数）。turns.py と後続ステップが使う。"""
from __future__ import annotations

import math

EARTH_RADIUS_M = 6_371_000.0

LatLngT = tuple[float, float]  # (lat, lng)


def haversine_m(a: LatLngT, b: LatLngT) -> float:
    lat1, lng1 = map(math.radians, a)
    lat2, lng2 = map(math.radians, b)
    dlat, dlng = lat2 - lat1, lng2 - lng1
    h = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlng / 2) ** 2
    return 2 * EARTH_RADIUS_M * math.asin(math.sqrt(h))


def bearing_deg(a: LatLngT, b: LatLngT) -> float:
    """a から b を見た方位。北 = 0、時計回り、0 <= 結果 < 360。"""
    lat1, lng1 = map(math.radians, a)
    lat2, lng2 = map(math.radians, b)
    dlng = lng2 - lng1
    x = math.sin(dlng) * math.cos(lat2)
    y = math.cos(lat1) * math.sin(lat2) - math.sin(lat1) * math.cos(lat2) * math.cos(dlng)
    return (math.degrees(math.atan2(x, y)) + 360.0) % 360.0


def heading_diff_deg(from_heading: float, to_heading: float) -> float:
    """方位の変化量。右回りが正、-180 < 結果 <= 180。"""
    d = (to_heading - from_heading + 180.0) % 360.0 - 180.0
    return 180.0 if d == -180.0 else d


def cumulative_m(path: list[LatLngT]) -> list[float]:
    """各頂点までの累積距離（m）。"""
    acc = [0.0]
    for p, q in zip(path, path[1:]):
        acc.append(acc[-1] + haversine_m(p, q))
    return acc


def bearing_into(path: list[LatLngT], idx: int, window_m: float = 10.0) -> float | None:
    """頂点 idx に「入ってくる」方位。idx から window_m 以上手前の頂点から idx を見る。"""
    if idx <= 0 or idx >= len(path):
        return None
    j, dist = idx, 0.0
    while j > 0 and dist < window_m:
        j -= 1
        dist += haversine_m(path[j], path[j + 1])
    return bearing_deg(path[j], path[idx]) if dist > 0 else None


def bearing_out_of(path: list[LatLngT], idx: int, window_m: float = 10.0) -> float | None:
    """頂点 idx から「出て行く」方位。idx から window_m 以上先の頂点を見る。"""
    if idx < 0 or idx >= len(path) - 1:
        return None
    j, dist = idx, 0.0
    while j < len(path) - 1 and dist < window_m:
        dist += haversine_m(path[j], path[j + 1])
        j += 1
    return bearing_deg(path[idx], path[j]) if dist > 0 else None


def nearest_vertex(path: list[LatLngT], p: LatLngT) -> int:
    return min(range(len(path)), key=lambda i: haversine_m(path[i], p))


def destination_point(p: LatLngT, bearing: float, distance_m: float) -> LatLngT:
    """p から bearing 方向へ distance_m 進んだ地点。"""
    lat1, lng1 = map(math.radians, p)
    br = math.radians(bearing)
    d = distance_m / EARTH_RADIUS_M
    lat2 = math.asin(math.sin(lat1) * math.cos(d) + math.cos(lat1) * math.sin(d) * math.cos(br))
    lng2 = lng1 + math.atan2(math.sin(br) * math.sin(d) * math.cos(lat1), math.cos(d) - math.sin(lat1) * math.sin(lat2))
    return (math.degrees(lat2), math.degrees(lng2))

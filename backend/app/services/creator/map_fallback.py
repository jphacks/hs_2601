"""Street View が見つからなかった地点に、経路を描いた地図画像（地理院タイル）を付ける。

参加者の画面で「写真がありません」にしないための最後の手段。作成者の写真がある地点は触らない。
元の Exploration は変更せず、新しいものを返す。
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path

import httpx

from app.imaging.route_tile_map import TileFetcher, render_route_tile_map
from app.schemas.exploration import Exploration, ExplorationPoint
from app.services.creator.arrow_geo import resample
from app.services.creator.cache import FileCache, cache_key
from app.services.creator.geo import LatLngT, project_to_path, travel_heading
from app.services.creator.route import decode_polyline

log = logging.getLogger(__name__)

GSI_TILE_URL = "https://cyberjapandata.gsi.go.jp/xyz/std/{z}/{x}/{y}.png"
TILE_TIMEOUT_S = 8.0
USER_AGENT = "hs_2601-wayfinder/1.0"
BEHIND_M = 50.0  # 矢印にする経路: 曲がり角の何 m 手前から
AHEAD_M = 50.0  # 何 m 先まで（曲がった先が矢印として読める長さ）
MAP_IMAGE_DIR = "images"


@dataclass(frozen=True)
class MapFallbackStats:
    drawn: list[int] = field(default_factory=list)


def gsi_tile_fetcher(cache: FileCache | None = None, http: httpx.Client | None = None) -> TileFetcher:
    client = http or httpx.Client(timeout=TILE_TIMEOUT_S, headers={"User-Agent": USER_AGENT})

    def fetch(z: int, x: int, y: int) -> bytes | None:
        key = cache_key("gsi-std", z, x, y)
        hit = cache.get_bytes(key, "png") if cache else None
        if hit is not None:
            return hit
        try:
            res = client.get(GSI_TILE_URL.format(z=z, x=x, y=y))
        except httpx.HTTPError as err:
            log.warning("地理院タイル %d/%d/%d を取れません: %s", z, x, y, err)
            return None
        if res.status_code != 200:
            return None
        if cache:
            cache.set_bytes(key, res.content, "png")
        return res.content

    return fetch


def _map_for_point(p: ExplorationPoint, route: list[LatLngT], fetch: TileFetcher) -> bytes:
    corner = (p.lat, p.lng)
    if len(route) >= 2:
        arc = project_to_path(route, corner)[1]
        start = arc if p.maneuver.upper() == "DEPART" else arc - BEHIND_M
        end = arc if p.turn == "arrive" else arc + AHEAD_M
        arrow = resample(route, max(0.0, start), end)
        up = travel_heading(route, max(0.0, arc - 10.0) if p.maneuver.upper() != "DEPART" else arc, stop_m=None)
    else:
        arrow, up = [], p.heading
    return render_route_tile_map(route, arrow, corner, up if up is not None else p.heading, p.turn, fetch)


def add_map_images(e: Exploration, out_dir: Path, fetch: TileFetcher) -> tuple[Exploration, MapFallbackStats]:
    """画像の無い地点（作成者の写真でない）に images/NNN_map.png を付け、image と arrow_image に入れる。"""
    route = decode_polyline(e.polyline) if e.polyline else []
    drawn: list[int] = []
    points: list[ExplorationPoint] = []
    for p in e.points:
        if p.image or p.image_source == "creator_photo":
            points.append(p)
            continue
        rel = f"{MAP_IMAGE_DIR}/{p.index:03d}_map.png"
        (out_dir / rel).parent.mkdir(parents=True, exist_ok=True)
        (out_dir / rel).write_bytes(_map_for_point(p, route, fetch))
        drawn.append(p.index)
        points.append(p.model_copy(update={"image": rel, "arrow_image": rel, "image_source": "map", "street_view": None}))
    return e.model_copy(update={"points": points}), MapFallbackStats(drawn)

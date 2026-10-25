"""テスト用: 作成者が歩きながら撮った写真を Street View で模倣し、photos.json を作る（手順 11）。

1. 通常の経路を 1 本計算し、採用された曲がり角（出発・到着を除く）から n 個を等間隔に選ぶ。
   足りなければポリラインの弧長を等分した点で補う。
2. 各点で公式パノラマを探し、進入方位を向いた 1 枚を取る。
3. 写真の座標はパノラマの撮影位置にする（撮影者が立っていた場所。GPS のずれも自然に入る）。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from app.external.google.routes import Route
from app.external.google.street_view import StreetViewClient
from app.schemas.creator_input import CreatorPhoto, PlanInput
from app.schemas.exploration import ExplorationPoint, Place
from app.services.creator.cache import FileCache, cache_key
from app.services.creator.geo import bearing_deg, cumulative_m
from app.services.creator.route import decode_polyline
from app.services.creator.streetview import StreetViewOptions, choose_pano
from app.services.creator.turns import extract_turns

PHOTO_DIR = "photos"
FAKE_ACCURACY_M = 10.0


@dataclass(frozen=True)
class FakePhotosStats:
    made: list[int] = field(default_factory=list)
    missing: list[int] = field(default_factory=list)  # Street View が無かった候補


def _evenly(items: list, n: int) -> list:
    if n <= 0 or not items:
        return []
    if len(items) <= n:
        return list(items)
    return [items[round((i + 1) * len(items) / (n + 1)) - 1] for i in range(n)]


def _arc_points(path: list[tuple[float, float]], n: int) -> list[ExplorationPoint]:
    """ポリラインの弧長を n+1 等分した内側の点。向きは次の頂点への方位。"""
    cum = cumulative_m(path)
    total = cum[-1]
    pts: list[ExplorationPoint] = []
    for i in range(1, n + 1):
        target = total * i / (n + 1)
        v = max(j for j, c in enumerate(cum) if c <= target)
        nxt = min(v + 1, len(path) - 1)
        heading = bearing_deg(path[v], path[nxt]) if nxt != v else 0.0
        pts.append(ExplorationPoint(index=i, lat=path[v][0], lng=path[v][1], heading=heading, maneuver="ARC", turn="straight",
                                    instruction="", distance_to_next_m=0))
    return pts


def pick_shoot_points(route: Route, origin: Place, destination: Place, n: int) -> list[ExplorationPoint]:
    turns = [p for p in extract_turns(route, origin, destination).exploration.points if p.maneuver.upper() not in ("DEPART", "ARRIVE")]
    chosen = _evenly(turns, n)
    if len(chosen) < n:
        extra = _arc_points(decode_polyline(route.polyline), n - len(chosen))
        chosen = sorted([*chosen, *extra], key=lambda p: (p.lat, p.lng))  # 経路順は後で頂点順に並べ直す
        path = decode_polyline(route.polyline)
        from app.services.creator.geo import nearest_vertex
        chosen.sort(key=lambda p: nearest_vertex(path, (p.lat, p.lng)))
    return chosen


def make_fake_photos(
    client: StreetViewClient, route: Route, origin: Place, destination: Place, n: int, out_dir: Path, name: str,
    cache: FileCache | None = None, opt: StreetViewOptions | None = None,
) -> tuple[PlanInput, FakePhotosStats]:
    opt = opt or StreetViewOptions(heading_mode="approach")
    (out_dir / PHOTO_DIR).mkdir(parents=True, exist_ok=True)
    photos: list[CreatorPhoto] = []
    made: list[int] = []
    missing: list[int] = []
    for i, p in enumerate(pick_shoot_points(route, origin, destination, n)):
        heading = p.heading or 0.0
        chosen = choose_pano(client, p, heading, opt)
        if chosen is None:
            missing.append(i)
            continue
        meta, _ = chosen
        key = cache_key("streetview", meta.pano_id, round(heading, 1), opt.fov, opt.pitch, opt.size)
        data = cache.get_bytes(key) if cache else None
        if data is None:
            data = client.image(meta.pano_id, heading=heading, fov=opt.fov, pitch=opt.pitch, size=opt.size)
            if cache:
                cache.set_bytes(key, data)
        seq = len(photos)
        pid = f"sv{seq}"
        rel = f"{PHOTO_DIR}/{pid}.jpg"
        (out_dir / rel).write_bytes(data)
        photos.append(CreatorPhoto(id=pid, seq=seq, image=rel, lat=meta.lat, lng=meta.lng, accuracy_m=FAKE_ACCURACY_M,
                                   taken_at=None, location_source="gps", caption=None))
        made.append(i)
    plan = PlanInput(name=name, origin={"query": origin.query, "lat": origin.lat, "lng": origin.lng},
                     destination={"query": destination.query, "lat": destination.lat, "lng": destination.lng}, photos=photos)
    (out_dir / "photos.json").write_text(plan.model_dump_json(indent=2), encoding="utf-8")
    return plan, FakePhotosStats(made, missing)

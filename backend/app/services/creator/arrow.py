"""ステップ 8: 採用画像に曲線の矢印を重ね、arrow_image を埋める。

経路は、地図の経路と画像の両方から決める。
(1) 地図の経路をカメラから見た形に投影した案内線（arrow_geo.py）を作る。VLM にはこれを画像に重ねて渡し、
    同じ道・同じ曲がり方のまま、画像に見える路面に合わせて引き直した arrow_path を返させている。
(2) VLM の線が案内線と一致していれば（arrow_fuse.consistent）、路面に合った VLM の線を使う（"fused"）。
(3) 一致しなければ案内線（"geo"）、案内線が無ければ VLM の線（"vlm"）、どちらも無ければ turn ごとの既定形。
作成者の写真（image_source == creator_photo）には描かず、写真をそのまま使う。
元の Exploration は変更せず、新しいものを返す。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from app.imaging.arrow import default_path, draw_arrow
from app.schemas.exploration import Exploration, ExplorationPoint
from app.services.creator.arrow_fuse import consistent
from app.services.creator.arrow_geo import geo_arrow_path
from app.services.creator.geo import LatLngT
from app.services.creator.route import decode_polyline


@dataclass(frozen=True)
class ArrowStats:
    drawn: list[int] = field(default_factory=list)
    with_geo_path: list[int] = field(default_factory=list)  # 経路の投影（案内線）で描いた
    with_fused_path: list[int] = field(default_factory=list)  # 案内線と一致した VLM の線で描いた
    with_vlm_path: list[int] = field(default_factory=list)
    skipped: list[int] = field(default_factory=list)  # 画像なし
    creator: list[int] = field(default_factory=list)  # 作成者の写真（描かない）


TURN_SIDE_X = {"left": 0.3, "right": 0.7}  # 左右折の終点はこの位置より外側に寄せる


def ensure_turn_side(path: list[tuple[float, float]], turn: str) -> list[tuple[float, float]]:
    """左右折なのに経路が曲がっていなければ、終点をその側へ寄せて曲線にする。"""
    limit = TURN_SIDE_X.get(turn)
    if limit is None or len(path) < 2:
        return path
    ex, ey = path[-1]
    ok = ex <= limit if turn == "left" else ex >= limit
    if ok:
        return path
    px, py = path[-2]
    bend = (px, (py + ey) / 2)  # 直前の点から縦に少し進んでから横へ
    return path[:-1] + [bend, (limit, ey)]


ArrowSource = str  # "fused" | "geo" | "vlm" | "default"


def _vlm_path(p: ExplorationPoint) -> list[tuple[float, float]] | None:
    if p.chosen_candidate is None or not p.candidates:
        return None
    sc = p.candidates[p.chosen_candidate].score
    return [(a.x, a.y) for a in sc.arrow_path] if sc and len(sc.arrow_path) >= 2 else None


def arrow_path_for(p: ExplorationPoint, route: list[LatLngT], prefer: ArrowSource = "geo") -> tuple[list[tuple[float, float]], ArrowSource]:
    """(経路, 由来)。prefer="vlm" なら案内線を使わず VLM の線だけを使う。"""
    vlm = _vlm_path(p)
    if prefer == "geo" and p.street_view is not None:
        geo = geo_arrow_path(route, p, p.street_view)
        if geo:
            if vlm and consistent(vlm, geo, p.turn):
                return vlm, "fused"
            return geo, "geo"
    if vlm:
        return ensure_turn_side(vlm, p.turn), "vlm"
    return default_path(p.turn), "default"


def draw_point_arrow(p: ExplorationPoint, out_dir: Path, route: list[LatLngT], prefer: ArrowSource = "geo") -> tuple[ExplorationPoint, ArrowSource]:
    assert p.image
    path, source = arrow_path_for(p, route, prefer)
    src = (out_dir / p.image).read_bytes()
    rel = f"images/{p.index:03d}_arrow.png"
    (out_dir / rel).write_bytes(draw_arrow(src, path, p.turn))
    return p.model_copy(update={"arrow_image": rel}), source


def draw_arrows(e: Exploration, out_dir: Path, prefer: ArrowSource = "geo") -> tuple[Exploration, ArrowStats]:
    route = decode_polyline(e.polyline)
    drawn: list[int] = []
    with_geo: list[int] = []
    with_fused: list[int] = []
    with_vlm: list[int] = []
    skipped: list[int] = []
    creator: list[int] = []
    points: list[ExplorationPoint] = []
    for p in e.points:
        if not p.image:
            skipped.append(p.index)
            points.append(p)
            continue
        if p.image_source == "creator_photo":
            creator.append(p.index)
            points.append(p.model_copy(update={"arrow_image": None}))
            continue
        q, source = draw_point_arrow(p, out_dir, route, prefer)
        drawn.append(p.index)
        if source == "geo":
            with_geo.append(p.index)
        elif source == "fused":
            with_fused.append(p.index)
        elif source == "vlm":
            with_vlm.append(p.index)
        points.append(q)
    return e.model_copy(update={"points": points}), ArrowStats(drawn, with_geo, with_fused, with_vlm, skipped, creator)

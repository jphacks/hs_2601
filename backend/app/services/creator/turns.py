"""ステップ 4: 経路から「迷う地点」（曲がり角）を抽出し、中間形式 route.json を組み立てる。

方針（docs/route-exploration.md 参照）:
- Routes API のステップ境界だけを候補にする。一本道のカーブはステップが切れないので候補にならない。
- maneuver が TURN/ROUNDABOUT/DEPART/STRAIGHT なら採用。NAME_CHANGE や空なら方位差で判定。
- 直前の採用点に近すぎる候補は統合する。
- 作成者の写真地点は判定に関係なく採用する。
- 屋内区間は今回スコープ外（案内文が空のステップとして方位差判定に流れるだけ）。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from app.external.google.routes import Route
from app.schemas.exploration import Exploration, ExplorationPoint, Place, Turn
from app.services.creator.geo import (
    LatLngT,
    bearing_into,
    bearing_out_of,
    cumulative_m,
    haversine_m,
    heading_diff_deg,
    nearest_vertex,
)
from app.services.creator.route import decode_polyline
from app.services.creator.text import normalize_instruction

# しきい値。実データで調整する
MIN_TURN_DEG = 20.0  # これ未満の方位変化は「道なり」とみなす
UTURN_DEG = 150.0
MERGE_DISTANCE_M = 5.0  # 直前の採用点からこの距離未満の候補は統合する
BEARING_WINDOW_M = 10.0  # 方位を測る窓の長さ

ALWAYS_ACCEPT_PREFIXES = ("TURN_", "UTURN_", "ROUNDABOUT_", "FERRY", "MERGE", "FORK_", "RAMP_")
RejectReason = Literal["small_heading_change", "too_close", "no_route"]


@dataclass(frozen=True)
class Candidate:
    """ステップ境界 1 つ分。判定の材料をすべて持つ（デバッグ表示用）。"""

    lat: float
    lng: float
    vertex: int  # 経路ポリライン上の頂点番号
    maneuver: str
    instruction: str
    heading_in: float | None
    heading_out: float | None
    delta_deg: float | None  # heading_in → heading_out の変化。右回り正
    source: Literal["step", "creator_photo", "arrive"]


@dataclass(frozen=True)
class Decision:
    candidate: Candidate
    accepted: bool
    turn: Turn | None = None
    reason: RejectReason | None = None


@dataclass(frozen=True)
class TurnsOutput:
    exploration: Exploration
    decisions: list[Decision] = field(default_factory=list)  # 候補ごとの判定（採用・不採用の両方）


def classify_turn(maneuver: str, delta_deg: float | None) -> Turn:
    m = maneuver.upper()
    if m == "ARRIVE":
        return "arrive"
    if "LEFT" in m:
        return "left"
    if "RIGHT" in m:
        return "right"
    if delta_deg is None:
        return "straight"
    if abs(delta_deg) > UTURN_DEG:
        return "right" if delta_deg > 0 else "left"  # U ターンは左右に丸める
    if delta_deg >= MIN_TURN_DEG:
        return "right"
    if delta_deg <= -MIN_TURN_DEG:
        return "left"
    return "straight"


def decide(c: Candidate, prev_accepted: Candidate | None, path: list[LatLngT]) -> Decision:
    m = c.maneuver.upper()
    # 目的地と作成者の写真は距離に関係なく採用する
    if prev_accepted is not None and c.source == "step":
        if haversine_m((c.lat, c.lng), (prev_accepted.lat, prev_accepted.lng)) < MERGE_DISTANCE_M:
            return Decision(c, False, reason="too_close")
    if c.source in ("creator_photo", "arrive") or m == "DEPART" or m == "STRAIGHT" or m.startswith(ALWAYS_ACCEPT_PREFIXES):
        return Decision(c, True, turn=classify_turn(c.maneuver, c.delta_deg))
    # NAME_CHANGE / 空: 方位差で判定
    if c.delta_deg is not None and abs(c.delta_deg) >= MIN_TURN_DEG:
        return Decision(c, True, turn=classify_turn("", c.delta_deg))
    return Decision(c, False, reason="small_heading_change")


def _candidate(path: list[LatLngT], vertex: int, maneuver: str, instruction: str, source: str) -> Candidate:
    h_in = bearing_into(path, vertex, BEARING_WINDOW_M)
    h_out = bearing_out_of(path, vertex, BEARING_WINDOW_M)
    delta = heading_diff_deg(h_in, h_out) if h_in is not None and h_out is not None else None
    lat, lng = path[vertex]
    return Candidate(lat, lng, vertex, maneuver, instruction, h_in, h_out, delta, source)  # type: ignore[arg-type]


def build_candidates(route: Route, path: list[LatLngT], creator_photos: list[LatLngT] | None = None) -> list[Candidate]:
    cands: list[Candidate] = []
    for s in route.steps:
        v = nearest_vertex(path, (s.start.lat, s.start.lng))
        cands.append(_candidate(path, v, s.maneuver, s.instruction, "step"))
    cands.append(_candidate(path, len(path) - 1, "ARRIVE", "目的地", "arrive"))
    for p in creator_photos or []:
        v = nearest_vertex(path, p)
        cands.append(_candidate(path, v, "CREATOR_PHOTO", "作成者の写真", "creator_photo"))
    # 経路順（頂点番号順）に並べる。同じ頂点なら作成者写真を優先
    return sorted(cands, key=lambda c: (c.vertex, 0 if c.source == "creator_photo" else 1))


def extract_turns(route: Route, origin: Place, destination: Place, creator_photos: list[LatLngT] | None = None) -> TurnsOutput:
    path = decode_polyline(route.polyline)
    if len(path) < 2:
        raise ValueError("経路のポリラインが空です")
    cum = cumulative_m(path)
    decisions: list[Decision] = []
    prev: Candidate | None = None
    for c in build_candidates(route, path, creator_photos):
        d = decide(c, prev, path)
        decisions.append(d)
        if d.accepted:
            prev = c
    accepted = [d for d in decisions if d.accepted]
    points: list[ExplorationPoint] = []
    for i, d in enumerate(accepted):
        c = d.candidate
        nxt = accepted[i + 1].candidate if i + 1 < len(accepted) else None
        dist = int(round(cum[nxt.vertex] - cum[c.vertex])) if nxt else 0
        # heading は「交差点に近づく向き」。出発点だけは出て行く向き
        heading = c.heading_in if c.heading_in is not None else c.heading_out
        points.append(
            ExplorationPoint(
                index=i,
                lat=c.lat,
                lng=c.lng,
                heading=heading,
                heading_out=c.heading_out,
                maneuver=c.maneuver,
                turn=d.turn or "straight",
                instruction=normalize_instruction(c.instruction, d.turn or "straight"),
                distance_to_next_m=max(dist, 0),
                image_source="creator_photo" if c.source == "creator_photo" else None,
            )
        )
    exploration = Exploration(
        origin=origin,
        destination=destination,
        polyline=route.polyline,
        total_distance_m=route.distance_m,
        points=points,
    )
    return TurnsOutput(exploration=exploration, decisions=decisions)

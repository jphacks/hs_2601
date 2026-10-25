"""写真を通る経路: 区間に分けて既存パイプラインを回し、結合して 1 つの Exploration にする。

- 区間 = 出発地 → 写真 1 → … → 写真 n → 目的地。写真順は入力順で固定（最適化しない）。
- 区間ごとに compute_route（ステップ 3）と extract_turns（ステップ 4）をそのまま使う。
- 結合では、区間 k の到着点と区間 k+1 の出発点を写真地点 1 つに統合する。
  向きは「区間 k の到着方位 → 区間 k+1 の出発方位」、turn はその差から決める。
- 写真 0 枚なら区間 1 本で、結果は extract_turns と同じ。
- 経路が取れない区間（同じ場所の写真など）は飛ばして警告に残し、処理は止めない。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

import polyline as polyline_codec

from app.external.google.routes import RoutesClient, RoutesError
from app.schemas.creator_input import CreatorPhoto
from app.schemas.exploration import CreatorPhotoMeta, Exploration, ExplorationPoint, Place
from app.services.creator.cache import FileCache
from app.services.creator.geo import haversine_m, heading_diff_deg
from app.services.creator.route import RouteOutput, compute_route, decode_polyline
from app.services.creator.turns import classify_turn, extract_turns

PHOTO_INSTRUCTION = "写真の地点"
SNAP_WARN_FACTOR = 3.0  # 撮影座標と経路の距離が accuracy_m の何倍を超えたら警告するか
DEFAULT_ACCURACY_M = 10.0
WarningKind = Literal["no_route", "snapped_far"]


@dataclass(frozen=True)
class Leg:
    index: int
    start: Place
    end: Place
    photo_at_end: CreatorPhoto | None  # 区間の終点が写真なら（目的地なら None）


@dataclass(frozen=True)
class LegWarning:
    kind: WarningKind
    photo_id: str | None
    message: str


@dataclass(frozen=True)
class MergedPlan:
    exploration: Exploration
    warnings: list[LegWarning] = field(default_factory=list)


def photo_place(photo: CreatorPhoto) -> Place:
    return Place(query=f"写真 {photo.seq}", lat=photo.lat, lng=photo.lng)


def split_legs(origin: Place, destination: Place, photos: list[CreatorPhoto]) -> list[Leg]:
    stops: list[tuple[Place, CreatorPhoto | None]] = [(origin, None), *((photo_place(p), p) for p in photos), (destination, None)]
    return [Leg(i, stops[i][0], stops[i + 1][0], stops[i + 1][1]) for i in range(len(stops) - 1)]


def plan_legs(client: RoutesClient, legs: list[Leg], cache: FileCache | None = None) -> tuple[list[RouteOutput | None], list[LegWarning]]:
    """区間ごとに経路を取る。取れない区間は None と警告。"""
    outputs: list[RouteOutput | None] = []
    warnings: list[LegWarning] = []
    for leg in legs:
        try:
            outputs.append(compute_route(client, leg.start, leg.end, [], cache))
        except RoutesError as e:
            outputs.append(None)
            pid = leg.photo_at_end.id if leg.photo_at_end else None
            warnings.append(LegWarning("no_route", pid, f"区間 {leg.index}（{leg.start.query} → {leg.end.query}）の経路が取れません: {e}"))
    return outputs, warnings


def _photo_point(photo: CreatorPhoto, arrive: ExplorationPoint, depart: ExplorationPoint) -> ExplorationPoint:
    """区間 k の到着点と区間 k+1 の出発点から写真地点を 1 つ作る。座標は吸着後（次区間の出発点）。"""
    h_in, h_out = arrive.heading, depart.heading_out
    delta = heading_diff_deg(h_in, h_out) if h_in is not None and h_out is not None else None
    snapped = haversine_m((photo.lat, photo.lng), (depart.lat, depart.lng))
    return ExplorationPoint(
        index=0, lat=depart.lat, lng=depart.lng, heading=h_in, heading_out=h_out,
        maneuver="CREATOR_PHOTO", turn=classify_turn("CREATOR_PHOTO", delta),
        instruction=photo.caption or PHOTO_INSTRUCTION, distance_to_next_m=depart.distance_to_next_m,
        image=photo.image, image_source="creator_photo", landmark=photo.caption,
        creator_photo=CreatorPhotoMeta(id=photo.id, lat=photo.lat, lng=photo.lng, accuracy_m=photo.accuracy_m, snapped_m=snapped),
    )


def _snap_warning(p: ExplorationPoint) -> LegWarning | None:
    cp = p.creator_photo
    assert cp is not None
    limit = (cp.accuracy_m or DEFAULT_ACCURACY_M) * SNAP_WARN_FACTOR
    if cp.snapped_m <= limit:
        return None
    return LegWarning("snapped_far", cp.id, f"写真 {cp.id} は経路から {cp.snapped_m:.0f} m 離れています（精度 {cp.accuracy_m or DEFAULT_ACCURACY_M:.0f} m）")


def _join_polylines(encoded: list[str]) -> list[tuple[float, float]]:
    path: list[tuple[float, float]] = []
    for enc in encoded:
        pts = decode_polyline(enc)
        if path and pts and path[-1] == pts[0]:
            pts = pts[1:]
        path.extend(pts)
    return path


def merge_legs(legs: list[Leg], outputs: list[RouteOutput | None], origin: Place, destination: Place) -> MergedPlan:
    """区間の結果を 1 つの Exploration にする。経路の無い区間は飛ばし、その終点の写真は前の写真に統合する。"""
    warnings: list[LegWarning] = []
    segments: list[tuple[Leg, list[ExplorationPoint], str, int]] = []  # (区間, 点列, ポリライン, 距離)
    for leg, out in zip(legs, outputs):
        if out is None:
            continue
        ex = extract_turns(out.route, leg.start, leg.end).exploration
        segments.append((leg, ex.points, ex.polyline, ex.total_distance_m))
    if not segments:
        raise ValueError("経路が取れた区間がありません")

    points: list[ExplorationPoint] = []
    pending_photo: CreatorPhoto | None = None  # 区間の終点にある写真。次の区間の先頭で統合する
    for i, (leg, pts, _, _) in enumerate(segments):
        body = list(pts)
        if pending_photo is not None:
            arrive = points.pop()  # 前区間の到着点を外し、写真地点に置き換える
            points.append(_photo_point(pending_photo, arrive, body[0]))
            body = body[1:]  # この区間の出発点も写真地点に含まれた
        points.extend(body)
        pending_photo = leg.photo_at_end
        if pending_photo is not None and i + 1 < len(segments):
            skipped = legs[leg.index + 1 : segments[i + 1][0].index]  # 間に飛ばした区間があれば、その写真は統合
            for s in skipped:
                if s.photo_at_end is not None:
                    warnings.append(LegWarning("no_route", s.photo_at_end.id, f"写真 {s.photo_at_end.id} は前の写真と同じ地点として扱います"))
    renumbered = [p.model_copy(update={"index": i}) for i, p in enumerate(points)]
    warnings.extend(w for p in renumbered if p.creator_photo and (w := _snap_warning(p)))
    path = _join_polylines([seg[2] for seg in segments])
    exploration = Exploration(
        origin=origin, destination=destination,
        polyline=polyline_codec.encode(path, precision=5),
        total_distance_m=sum(seg[3] for seg in segments), points=renumbered,
    )
    return MergedPlan(exploration, warnings)

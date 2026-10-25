"""矢印の点列を、経路のポリライン（道路の中心線）をカメラから見た形に投影して作る。

VLM が画像を見て点を打つ方式は路面から外れることがある。経路は道路に沿っているので、
パノラマの位置・向き・画角が分かれば、曲がり角の前後の経路を画像に投影するだけで道なりの点列になる。
"""
from __future__ import annotations

from dataclasses import dataclass

from app.imaging.projection import Camera, in_frame, project_ground
from app.schemas.exploration import ExplorationPoint, StreetViewMeta
from app.services.creator.geo import LatLngT, cumulative_m, destination_point, nearest_vertex, point_at, project_to_path

BEHIND_M = 60.0  # 曲がり角の何 m 手前から経路を辿るか
AHEAD_M = 40.0  # 曲がった先を何 m まで描くか（遠すぎると消失点付近で点が固まる）
STEP_M = 2.0  # 投影する点の間隔
MIN_POINTS = 3
FOOT_Y = 0.95  # 最初の点がこれより上なら足元から線を伸ばす
FOOT_GAP = 0.12
SIMPLIFY_EPS = 0.015  # 投影後の点列を間引く許容誤差（正規化座標）

XY = tuple[float, float]


def camera_position(p: ExplorationPoint, sv: StreetViewMeta) -> LatLngT:
    """パノラマの位置。メタに無ければ offset_m から推定する（古い route.json 用）。"""
    if sv.lat is not None and sv.lng is not None:
        return (sv.lat, sv.lng)
    if sv.offset_m < 0 and p.heading_out is not None:
        return destination_point((p.lat, p.lng), p.heading_out, -sv.offset_m)
    heading = p.heading if p.heading is not None else 0.0
    direction = heading if p.maneuver.upper() == "DEPART" else (heading + 180.0) % 360.0
    return destination_point((p.lat, p.lng), direction, sv.offset_m)


SNAP_M = 8.0  # 経路からこの距離以内のカメラは、経路の上に立っているとみなして寄せる


def snapped_camera(path: list[LatLngT], p: ExplorationPoint, sv: StreetViewMeta) -> LatLngT:
    """カメラ位置を経路線の上に寄せる。地図の経路線は道の中心から数 m ずれていることが多く、
    そのまま投影すると矢印が足元から横にずれる。歩く向きの距離（どこで曲がるか）はそのまま保つ。"""
    pos = camera_position(p, sv)
    off, arc = project_to_path(path, pos)
    return point_at(path, arc) if off <= SNAP_M else pos


def resample(path: list[LatLngT], start_m: float, end_m: float, step_m: float = STEP_M) -> list[LatLngT]:
    """経路の弧長 start_m〜end_m を step_m ごとに刻む（頂点間は線形補間）。"""
    cum = cumulative_m(path)
    start_m, end_m = max(0.0, start_m), min(cum[-1], end_m)
    out: list[LatLngT] = []
    s = start_m
    j = 0
    while s <= end_m + 1e-9:
        while j < len(path) - 2 and cum[j + 1] < s:
            j += 1
        seg = cum[j + 1] - cum[j]
        t = 0.0 if seg <= 0 else (s - cum[j]) / seg
        out.append((path[j][0] + (path[j + 1][0] - path[j][0]) * t, path[j][1] + (path[j + 1][1] - path[j][1]) * t))
        s += step_m
    return out


def route_window(path: list[LatLngT], p: ExplorationPoint) -> tuple[list[LatLngT], int]:
    """曲がり角の前後の経路を細かく刻む。(点列, 曲がり角に当たる点の番号)"""
    v = nearest_vertex(path, (p.lat, p.lng))
    at = cumulative_m(path)[v]
    ahead = AHEAD_M if p.turn != "arrive" else 0.0
    start = max(0.0, at - BEHIND_M)
    pts = resample(path, start, at + ahead)
    corner = min(range(len(pts)), key=lambda i: abs(start + i * STEP_M - at)) if pts else 0
    return pts, corner


MIN_PROGRESS = 0.03  # 始点より終点が上（奥）にあること


def visible_runs(xys: list[XY | None]) -> list[tuple[int, list[XY]]]:
    """画像内に入る連続区間を (開始番号, 点列) で返す。"""
    runs: list[tuple[int, list[XY]]] = []
    cur: list[XY] = []
    start = 0
    for i, xy in enumerate(xys):
        if in_frame(xy):
            if not cur:
                start = i
            cur.append(xy)  # type: ignore[arg-type]
        elif cur:
            runs.append((start, cur))
            cur = []
    if cur:
        runs.append((start, cur))
    return runs


def forward_runs(runs: list[tuple[int, list[XY]]]) -> list[tuple[int, list[XY]]]:
    """歩く向きに奥へ進む区間だけ残す（カメラが後ろ向きのとき手前へ戻る区間は使わない）。"""
    return [(s, r) for s, r in runs if len(r) >= MIN_POINTS and r[0][1] - r[-1][1] >= MIN_PROGRESS]


def choose_run(runs: list[tuple[int, list[XY]]], corner: int) -> tuple[int, list[XY]] | None:
    """曲がり角を含む区間を優先し、同点なら長いもの。"""
    forward = forward_runs(runs)
    if not forward:
        return None
    return max(forward, key=lambda t: (spans(t, corner), len(t[1])))


def spans(run: tuple[int, list[XY]], corner: int) -> bool:
    """区間が曲がり角そのものを含む（手前から曲がった先まで見えている）。"""
    start, pts = run
    return start <= corner <= start + len(pts) - 1


def clip_to_frame(outside: XY, inside: XY) -> XY:
    """枠外の点から枠内の点へ向かう線分が枠の縁と交わる点。"""
    t = 0.0  # 両方の座標が枠内に入った時点（遅い方）で線を始める
    for o, i in ((outside[0], inside[0]), (outside[1], inside[1])):
        if o < 0.0:
            t = max(t, (0.0 - o) / (i - o))
        elif o > 1.0:
            t = max(t, (1.0 - o) / (i - o))
    return (outside[0] + (inside[0] - outside[0]) * t, outside[1] + (inside[1] - outside[1]) * t)


def _entry(xys: list[XY | None], start: int, first: XY) -> XY | None:
    """区間の直前の点が枠外（カメラの脇を通る経路）なら、枠の縁から線を始める。
    直前の点が無い・カメラの後ろにある場合は足元から始める。"""
    prev = xys[start - 1] if start > 0 else None
    if prev is not None:
        return clip_to_frame(prev, first)
    return (0.5, FOOT_Y) if first[1] < FOOT_Y - FOOT_GAP else None


def simplify(pts: list[XY], eps: float = SIMPLIFY_EPS) -> list[XY]:
    """Douglas-Peucker。投影で密集した点や消失点付近の小さなブレを落とす。"""
    if len(pts) <= 2:
        return list(pts)
    (x0, y0), (x1, y1) = pts[0], pts[-1]
    dx, dy = x1 - x0, y1 - y0
    norm = (dx * dx + dy * dy) ** 0.5

    def dist(q: XY) -> float:
        if norm == 0:
            return ((q[0] - x0) ** 2 + (q[1] - y0) ** 2) ** 0.5
        return abs(dx * (y0 - q[1]) - (x0 - q[0]) * dy) / norm

    k = max(range(1, len(pts) - 1), key=lambda i: dist(pts[i]))
    if dist(pts[k]) <= eps:
        return [pts[0], pts[-1]]
    return simplify(pts[: k + 1], eps)[:-1] + simplify(pts[k:], eps)


def geo_arrow_path(path: list[LatLngT], p: ExplorationPoint, sv: StreetViewMeta) -> list[XY] | None:
    """道なりの点列（正規化座標）。描けるだけの点が画像に入らなければ None。"""
    if len(path) < 2:
        return None
    lat, lng = snapped_camera(path, p, sv)
    cam = Camera(lat=lat, lng=lng, heading=sv.heading, fov=float(sv.fov), pitch=float(sv.pitch))
    window, corner = route_window(path, p)
    xys = [project_ground(cam, g) for g in window]
    chosen = choose_run(visible_runs(xys), corner)
    if chosen is None:
        return None
    start, pts = chosen
    entry = _entry(xys, start, pts[0])
    return simplify([entry, *pts] if entry else pts)


def projected_corner(path: list[LatLngT], p: ExplorationPoint, sv: StreetViewMeta) -> XY | None:
    """曲がる地点（この地点の座標）の画像内座標。枠外・後ろなら None。"""
    if len(path) < 2:
        return None
    lat, lng = snapped_camera(path, p, sv)
    cam = Camera(lat=lat, lng=lng, heading=sv.heading, fov=float(sv.fov), pitch=float(sv.pitch))
    xy = project_ground(cam, (p.lat, p.lng))
    return xy if xy is not None and in_frame(xy) else None


START_X_RANGE = (0.25, 0.75)  # 歩行者の視点なら経路は画面下の中央寄りから始まる
START_Y_MIN = 0.7


@dataclass(frozen=True)
class GeoVisibility:
    visible: bool  # 歩く向きに進む経路が画像内に見える
    includes_corner: bool  # 曲がり角（この地点）以降まで見える
    starts_at_feet: bool  # 経路が足元（画面下の中央寄り）から始まる = 歩行者の視点
    n_points: int
    official: bool = True  # Google 公式撮影（ユーザー投稿は屋内・夜景が混ざる）

    @property
    def rank(self) -> tuple[bool, bool, bool, bool]:
        return (self.visible, self.official, self.includes_corner, self.starts_at_feet)


def is_official(sv: StreetViewMeta) -> bool:
    return "google" in (sv.copyright or "").lower()


def geo_visibility(path: list[LatLngT], p: ExplorationPoint, sv: StreetViewMeta) -> GeoVisibility:
    """候補画像の選定用。経路の投影がどれだけ画像に入るか。"""
    official = is_official(sv)
    if len(path) < 2:
        return GeoVisibility(False, False, False, 0, official)
    lat, lng = snapped_camera(path, p, sv)
    cam = Camera(lat=lat, lng=lng, heading=sv.heading, fov=float(sv.fov), pitch=float(sv.pitch))
    window, corner = route_window(path, p)
    best = choose_run(visible_runs([project_ground(cam, g) for g in window]), corner)
    if best is None:
        return GeoVisibility(False, False, False, 0, official)
    x0, y0 = best[1][0]
    at_feet = START_X_RANGE[0] <= x0 <= START_X_RANGE[1] and y0 >= START_Y_MIN
    return GeoVisibility(True, spans(best, corner), at_feet, len(best[1]), official)

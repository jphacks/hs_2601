"""VLM に渡す経路情報の文章化。

画像だけでは「どの向きでどこを見ているか」が分からないので、経路（Routes API のポリライン）と
各候補画像の撮影位置・向き、そして経路を画像に投影した線を文章にしてプロンプトに添える。
"""
from __future__ import annotations

from app.schemas.exploration import ExplorationPoint, ImageCandidate, StreetViewMeta
from app.services.creator.arrow_geo import camera_position, geo_arrow_path, is_official, projected_corner
from app.services.creator.geo import LatLngT, bearing_deg, cumulative_m, haversine_m, heading_diff_deg, nearest_vertex

COMPASS = ("北", "北東", "東", "南東", "南", "南西", "西", "北西")
PROFILE_M = (-60.0, -40.0, -20.0, -10.0, 0.0, 10.0, 20.0, 40.0)  # 交差点を 0 とした弧長
COORD_DIGITS = 6  # 約 0.1 m


def compass(deg: float) -> str:
    return COMPASS[int(((deg % 360.0) + 22.5) // 45.0) % 8]


def fmt_heading(deg: float) -> str:
    return f"{deg:.0f}°（{compass(deg)}）"


def fmt_latlng(pt: LatLngT) -> str:
    return f"({pt[0]:.{COORD_DIGITS}f}, {pt[1]:.{COORD_DIGITS}f})"


def relative(from_heading: float, to_heading: float) -> str:
    """進入方向から見た向き。例「右 35°」「ほぼ同じ向き」「後ろ向き」"""
    d = heading_diff_deg(from_heading, to_heading)
    if abs(d) < 10.0:
        return "ほぼ同じ向き"
    if abs(d) > 150.0:
        return f"後ろ向き（{abs(d):.0f}°）"
    return f"{'右' if d > 0 else '左'} {abs(d):.0f}°"


def _at(path: list[LatLngT], arc_m: float) -> LatLngT | None:
    """弧長 arc_m の地点（頂点間は線形補間）。範囲外なら None。"""
    cum = cumulative_m(path)
    if arc_m < -1e-6 or arc_m > cum[-1] + 1e-6:
        return None
    arc_m = min(max(arc_m, 0.0), cum[-1])
    for j in range(len(path) - 1):
        if cum[j] <= arc_m <= cum[j + 1]:
            seg = cum[j + 1] - cum[j]
            t = 0.0 if seg <= 0 else (arc_m - cum[j]) / seg
            return (path[j][0] + (path[j + 1][0] - path[j][0]) * t, path[j][1] + (path[j + 1][1] - path[j][1]) * t)
    return path[-1]


def route_profile(path: list[LatLngT], p: ExplorationPoint) -> list[tuple[float, LatLngT, float | None]]:
    """交差点の前後の経路を (交差点からの弧長, 緯度経度, その先へ進む方位) で並べる。"""
    at = cumulative_m(path)[nearest_vertex(path, (p.lat, p.lng))]
    out: list[tuple[float, LatLngT, float | None]] = []
    for off in PROFILE_M:
        pt = _at(path, at + off)
        if pt is None:
            continue
        nxt = _at(path, at + off + 5.0)
        out.append((off, pt, bearing_deg(pt, nxt) if nxt and haversine_m(pt, nxt) > 0.5 else None))
    return out


def route_context(p: ExplorationPoint, route: list[LatLngT] | None) -> str:
    """この地点の経路情報（交差点の座標・進入/退出方位・前後の経路）。"""
    lines = [f"- 地点の緯度経度: {fmt_latlng((p.lat, p.lng))}"]
    if p.heading is not None:
        lines.append(f"- 進入方位（この地点へ歩いて来る向き）: {fmt_heading(p.heading)}")
    if p.heading_out is not None:
        lines.append(f"- 退出方位（この地点から進む向き）: {fmt_heading(p.heading_out)}")
        if p.heading is not None:
            lines.append(f"- 向きの変化: {relative(p.heading, p.heading_out)}")
    if route and len(route) >= 2:
        lines.append("- 前後の経路（交差点を 0 m として、手前が負）:")
        for off, pt, hd in route_profile(route, p):
            where = "この地点" if off == 0 else (f"{-off:.0f} m 手前" if off < 0 else f"{off:.0f} m 先")
            head = f"、次へ進む方位 {fmt_heading(hd)}" if hd is not None else ""
            lines.append(f"    - {where}: {fmt_latlng(pt)}{head}")
    return "\n".join(lines)


def _position_desc(p: ExplorationPoint, sv: StreetViewMeta, cam: LatLngT) -> str:
    d = haversine_m(cam, (p.lat, p.lng))
    if d < 3.0:
        return "交差点のほぼ上"
    b = bearing_deg((p.lat, p.lng), cam)
    if p.heading_out is not None and abs(heading_diff_deg(p.heading_out, b)) < 45.0:
        return f"曲がった先の道路に {d:.0f} m 入った位置"
    if p.heading is not None and abs(heading_diff_deg((p.heading + 180.0) % 360.0, b)) < 45.0:
        return f"交差点の {d:.0f} m 手前"
    return f"交差点から {compass(b)} へ {d:.0f} m"


def _projection_desc(p: ExplorationPoint, sv: StreetViewMeta, cam: LatLngT, route: list[LatLngT] | None) -> list[str]:
    if not route or len(route) < 2:
        return []
    corner = projected_corner(route, p, sv)
    lines = []
    if corner is not None:
        lines.append(f"    - 曲がる地点の画像内座標（画像の水色の丸）: ({corner[0]:.2f}, {corner[1]:.2f})")
    else:
        lines.append("    - 曲がる地点は画像の枠外（または後ろ）")
    path = geo_arrow_path(route, p, sv)
    if path:
        pts = " → ".join(f"({x:.2f}, {y:.2f})" for x, y in path)
        lines.append(f"    - 案内線（地図の経路を画像に写したもの。画像に水色の線で描いてある）: {pts}")
    else:
        lines.append("    - 案内線: この画像には歩く向きの経路が映らない")
    return lines


def candidate_context(p: ExplorationPoint, cands: list[ImageCandidate], route: list[LatLngT] | None) -> str:
    """各候補画像の撮影位置・向きと、経路の投影。"""
    blocks: list[str] = []
    for i, c in enumerate(cands):
        sv = c.street_view
        cam = camera_position(p, sv)
        head = [f"- 画像 {i}: 撮影位置 {fmt_latlng(cam)}（{_position_desc(p, sv, cam)}）"]
        rel = f"、進入方位から見て {relative(p.heading, sv.heading)}" if p.heading is not None else ""
        head.append(f"    - カメラの向き: {fmt_heading(sv.heading)}{rel}、水平画角 {sv.fov}°、ピッチ {sv.pitch}°")
        meta = f"    - 撮影: {'Google 公式' if is_official(sv) else 'ユーザー投稿'}" + (f"、{sv.date}" if sv.date else "")
        head.append(meta)
        blocks.append("\n".join(head + _projection_desc(p, sv, cam, route)))
    return "\n".join(blocks) or "（候補なし）"

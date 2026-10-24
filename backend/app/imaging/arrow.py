"""画像に曲線の矢印を重ねる（Pillow）。純粋な描画だけで、route.json のことは知らない。"""
from __future__ import annotations

import math
from io import BytesIO

from PIL import Image, ImageDraw

Point = tuple[float, float]

COLORS = {"left": (242, 145, 0), "right": (123, 31, 162), "straight": (26, 115, 232), "arrive": (211, 47, 47)}
OUTLINE = (255, 255, 255)


def default_path(turn: str) -> list[Point]:
    """VLM の経路が無いときの既定形。足元から奥へ進み、左右は横へ抜ける。"""
    if turn == "left":
        return [(0.5, 0.95), (0.5, 0.62), (0.42, 0.52), (0.12, 0.5)]
    if turn == "right":
        return [(0.5, 0.95), (0.5, 0.62), (0.58, 0.52), (0.88, 0.5)]
    return [(0.5, 0.95), (0.5, 0.45)]


def catmull_rom(points: list[Point], samples_per_segment: int = 16) -> list[Point]:
    """制御点を通る滑らかな曲線を折れ線に展開する。"""
    if len(points) < 3:
        return list(points)
    pts = [points[0], *points, points[-1]]
    out: list[Point] = []
    for i in range(1, len(pts) - 2):
        p0, p1, p2, p3 = pts[i - 1], pts[i], pts[i + 1], pts[i + 2]
        for k in range(samples_per_segment):
            t = k / samples_per_segment
            t2, t3 = t * t, t * t * t
            x = 0.5 * ((2 * p1[0]) + (-p0[0] + p2[0]) * t + (2 * p0[0] - 5 * p1[0] + 4 * p2[0] - p3[0]) * t2 + (-p0[0] + 3 * p1[0] - 3 * p2[0] + p3[0]) * t3)
            y = 0.5 * ((2 * p1[1]) + (-p0[1] + p2[1]) * t + (2 * p0[1] - 5 * p1[1] + 4 * p2[1] - p3[1]) * t2 + (-p0[1] + 3 * p1[1] - 3 * p2[1] + p3[1]) * t3)
            out.append((x, y))
    out.append(points[-1])
    return out


def _arrowhead(tip: Point, tail: Point, size: float) -> list[Point]:
    ang = math.atan2(tip[1] - tail[1], tip[0] - tail[0])
    left = (tip[0] - size * math.cos(ang - math.pi / 6), tip[1] - size * math.sin(ang - math.pi / 6))
    right = (tip[0] - size * math.cos(ang + math.pi / 6), tip[1] - size * math.sin(ang + math.pi / 6))
    return [tip, left, right]


def draw_arrow(image: bytes, path: list[Point], turn: str) -> bytes:
    """path は 0〜1 の正規化座標。JPEG バイト列を受け取り、矢印入りの JPEG を返す。"""
    img = Image.open(BytesIO(image)).convert("RGB")
    w, h = img.size
    pts = [(x * w, y * h) for x, y in (path if len(path) >= 2 else default_path(turn))]
    curve = catmull_rom(pts)
    color = COLORS.get(turn, COLORS["straight"])
    width = max(6, int(w * 0.028))
    head = width * 2.6

    # 矢じりの分だけ線を手前で止める
    tip, prev = curve[-1], curve[-2]
    seg = math.hypot(tip[0] - prev[0], tip[1] - prev[1]) or 1.0
    stop = (tip[0] - (tip[0] - prev[0]) / seg * head * 0.7, tip[1] - (tip[1] - prev[1]) / seg * head * 0.7)
    line = curve[:-1] + [stop]

    draw = ImageDraw.Draw(img)
    for stroke, c in ((width + 6, OUTLINE), (width, color)):
        draw.line(line, fill=c, width=stroke, joint="curve")
        for p in (line[0], line[-1]):
            draw.ellipse([p[0] - stroke / 2, p[1] - stroke / 2, p[0] + stroke / 2, p[1] + stroke / 2], fill=c)
    tri = _arrowhead(tip, prev, head)
    draw.polygon(tri, fill=OUTLINE, outline=OUTLINE, width=3)
    inner = _arrowhead(tip, prev, head - 4)
    draw.polygon(inner, fill=color)

    buf = BytesIO()
    img.save(buf, format="JPEG", quality=90)
    return buf.getvalue()

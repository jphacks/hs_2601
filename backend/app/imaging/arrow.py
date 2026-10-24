"""画像に矢印を重ねる（Pillow）。VLM が打った点を直線で順につなぎ、終点に矢じりを付ける。
単色（縁取りなし）。純粋な描画だけで、route.json のことは知らない。"""
from __future__ import annotations

import math
from io import BytesIO

from PIL import Image, ImageDraw

Point = tuple[float, float]

COLORS = {"left": (242, 145, 0), "right": (123, 31, 162), "straight": (26, 115, 232), "arrive": (211, 47, 47)}


def default_path(turn: str) -> list[Point]:
    """VLM の点列が無いときの既定形。足元から奥へ進み、左右は横へ抜ける。"""
    if turn == "left":
        return [(0.5, 0.95), (0.5, 0.85), (0.5, 0.75), (0.48, 0.65), (0.4, 0.57), (0.28, 0.52), (0.14, 0.5)]
    if turn == "right":
        return [(0.5, 0.95), (0.5, 0.85), (0.5, 0.75), (0.52, 0.65), (0.6, 0.57), (0.72, 0.52), (0.86, 0.5)]
    return [(0.5, 0.95), (0.5, 0.82), (0.5, 0.69), (0.5, 0.56), (0.5, 0.45)]


def _dedupe(pts: list[Point], min_dist: float) -> list[Point]:
    """近すぎる点（矢じりの向きが乱れる原因）を間引く。"""
    out: list[Point] = [pts[0]]
    for p in pts[1:]:
        if math.hypot(p[0] - out[-1][0], p[1] - out[-1][1]) >= min_dist:
            out.append(p)
    if len(out) < 2 and len(pts) >= 2:
        out = [pts[0], pts[-1]]
    return out


def _arrowhead(tip: Point, tail: Point, size: float) -> list[Point]:
    ang = math.atan2(tip[1] - tail[1], tip[0] - tail[0])
    left = (tip[0] - size * math.cos(ang - math.pi / 6), tip[1] - size * math.sin(ang - math.pi / 6))
    right = (tip[0] - size * math.cos(ang + math.pi / 6), tip[1] - size * math.sin(ang + math.pi / 6))
    return [tip, left, right]


def draw_arrow(image: bytes, path: list[Point], turn: str) -> bytes:
    """path は 0〜1 の正規化座標の点列。点を直線で結び、終点に矢じりを付けた JPEG を返す。"""
    img = Image.open(BytesIO(image)).convert("RGB")
    w, h = img.size
    norm = path if len(path) >= 2 else default_path(turn)
    pts = _dedupe([(x * w, y * h) for x, y in norm], min_dist=w * 0.02)
    color = COLORS.get(turn, COLORS["straight"])
    width = max(6, int(w * 0.024))
    head = width * 2.4

    # 矢じりの分だけ最後の線分を手前で止める
    tip, prev = pts[-1], pts[-2]
    seg = math.hypot(tip[0] - prev[0], tip[1] - prev[1]) or 1.0
    stop = (tip[0] - (tip[0] - prev[0]) / seg * head * 0.7, tip[1] - (tip[1] - prev[1]) / seg * head * 0.7)
    line = pts[:-1] + [stop]

    draw = ImageDraw.Draw(img)
    draw.line(line, fill=color, width=width, joint="curve")
    r = width / 2
    for p in line:  # 折れ目と端を丸める
        draw.ellipse([p[0] - r, p[1] - r, p[0] + r, p[1] + r], fill=color)
    draw.polygon(_arrowhead(tip, prev, head), fill=color)

    buf = BytesIO()
    img.save(buf, format="JPEG", quality=90)
    return buf.getvalue()

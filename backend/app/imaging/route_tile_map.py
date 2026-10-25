"""地理院タイルを並べて、地点のまわりの経路を描いた地図画像を作る（Pillow）。純粋な描画だけ。

Street View が無い地点でも必ず 1 枚画像を出すための最後の手段。歩く向きが上になるよう回転し、
今の道 → 曲がる先を矢印で描く。タイルが取れなくても、背景なしで経路と矢印だけは描く。
"""
from __future__ import annotations

import math
from collections.abc import Callable
from io import BytesIO
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from app.imaging.arrow import COLORS

LatLng = tuple[float, float]
TileFetcher = Callable[[int, int, int], bytes | None]  # (z, x, y) → PNG。取れなければ None

TILE = 256
ZOOM = 18
OUT_W, OUT_H = 640, 480
ANCHOR = (0.5, 0.62)  # 曲がる地点を置く位置（少し下 = 先の道が多く見える）
ROUTE_COLOR = (66, 133, 244, 150)
BACKGROUND = (238, 238, 232)
ATTRIBUTION = "地理院タイル"
FONT_CANDIDATES = (
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/opentype/noto/NotoSerifCJK-Regular.ttc",
)


def world_px(p: LatLng, z: int = ZOOM) -> tuple[float, float]:
    """Web メルカトルの全体ピクセル座標。"""
    n = TILE * 2 ** z
    lat = math.radians(p[0])
    x = (p[1] + 180.0) / 360.0 * n
    y = (1.0 - math.log(math.tan(lat) + 1.0 / math.cos(lat)) / math.pi) / 2.0 * n
    return x, y


def _font(size: int) -> ImageFont.ImageFont:
    for path in FONT_CANDIDATES:
        if Path(path).exists():
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def _background(center: tuple[float, float], radius: int, fetch: TileFetcher) -> Image.Image:
    """center のまわり radius px を覆うタイルを並べる。取れないタイルは無地。"""
    size = radius * 2
    img = Image.new("RGB", (size, size), BACKGROUND)
    left, top = center[0] - radius, center[1] - radius
    for ty in range(int(top // TILE), int((top + size) // TILE) + 1):
        for tx in range(int(left // TILE), int((left + size) // TILE) + 1):
            data = fetch(ZOOM, tx, ty)
            if not data:
                continue
            try:
                tile = Image.open(BytesIO(data)).convert("RGB")
            except OSError:
                continue
            img.paste(tile, (round(tx * TILE - left), round(ty * TILE - top)))
    return img


def _arrowhead(d: ImageDraw.ImageDraw, tip: tuple[float, float], tail: tuple[float, float], size: float, color) -> None:
    ang = math.atan2(tip[1] - tail[1], tip[0] - tail[0])
    pts = [tip] + [(tip[0] - size * math.cos(ang + s * math.pi / 6), tip[1] - size * math.sin(ang + s * math.pi / 6)) for s in (-1, 1)]
    d.polygon(pts, fill=color)


def render_route_tile_map(route: list[LatLng], arrow: list[LatLng], corner: LatLng, heading_up: float | None,
                          turn: str, fetch: TileFetcher) -> bytes:
    """route: 経路全体、arrow: 曲がり角の手前 → 先の経路（矢印にする部分）、corner: 曲がる地点。PNG を返す。"""
    radius = math.ceil(math.hypot(OUT_W, OUT_H) / 2 * 1.3)  # 回転しても隅が欠けない大きさ
    c = world_px(corner)
    img = _background(c, radius, fetch).convert("RGBA")
    to_local = lambda p: (world_px(p)[0] - c[0] + radius, world_px(p)[1] - c[1] + radius)  # noqa: E731

    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(overlay)
    if len(route) >= 2:
        d.line([to_local(p) for p in route], fill=ROUTE_COLOR, width=10, joint="curve")
    color = COLORS.get(turn, COLORS["straight"]) + (255,)
    if len(arrow) >= 2:
        pts = [to_local(p) for p in arrow]
        d.line(pts, fill=color, width=14, joint="curve")
        _arrowhead(d, pts[-1], pts[-2], 34, color)
    cx, cy = to_local(corner)
    d.ellipse([cx - 11, cy - 11, cx + 11, cy + 11], fill=(255, 255, 255, 255), outline=color, width=6)
    img = Image.alpha_composite(img, overlay)

    if heading_up is not None:  # 歩く向きを上にする（PIL の rotate は反時計回り）
        img = img.rotate(heading_up, resample=Image.BICUBIC, center=(radius, radius), fillcolor=BACKGROUND + (255,))
    left = radius - OUT_W * ANCHOR[0]
    top = radius - OUT_H * ANCHOR[1]
    out = img.crop((round(left), round(top), round(left) + OUT_W, round(top) + OUT_H)).convert("RGB")

    od = ImageDraw.Draw(out)
    font = _font(14)
    tw = od.textlength(ATTRIBUTION, font=font)
    od.rectangle([OUT_W - tw - 12, OUT_H - 24, OUT_W, OUT_H], fill=(255, 255, 255))
    od.text((OUT_W - tw - 6, OUT_H - 22), ATTRIBUTION, fill=(60, 60, 60), font=font)
    buf = BytesIO()
    out.save(buf, format="PNG")
    return buf.getvalue()

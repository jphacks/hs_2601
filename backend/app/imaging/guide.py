"""VLM に渡す評価用画像に、地図の経路を投影した「案内線」を重ねる（Pillow）。

案内線は地図の経路そのもので、数 m の誤差がある。VLM はこれを手がかりに、画像に見える路面に合わせて
矢印を引き直す。採用画像（参加者に見せる画像）には描かない。
"""
from __future__ import annotations

from io import BytesIO

from PIL import Image, ImageDraw

Point = tuple[float, float]

GUIDE_COLOR = (0, 229, 255)  # 水色。矢印の色（橙・紫・青・赤）と区別できる
GUIDE_WIDTH_RATIO = 0.008
CORNER_RADIUS_RATIO = 0.018


def draw_guide(image: bytes, path: list[Point], corner: Point | None = None) -> bytes:
    """正規化座標の点列を細い線で重ねた JPEG を返す。corner があれば曲がる位置に丸を付ける。"""
    im = Image.open(BytesIO(image)).convert("RGB")
    w, h = im.size
    d = ImageDraw.Draw(im)
    if len(path) >= 2:
        d.line([(x * w, y * h) for x, y in path], fill=GUIDE_COLOR, width=max(2, round(w * GUIDE_WIDTH_RATIO)), joint="curve")
    if corner is not None:
        r = max(4, round(w * CORNER_RADIUS_RATIO))
        cx, cy = corner[0] * w, corner[1] * h
        d.ellipse([cx - r, cy - r, cx + r, cy + r], outline=GUIDE_COLOR, width=max(2, r // 3))
    buf = BytesIO()
    im.save(buf, format="JPEG", quality=90)
    return buf.getvalue()

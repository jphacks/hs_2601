"""地図の経路の投影（案内線）と、VLM が画像の路面に合わせて引いた線を突き合わせる。

VLM の線が案内線と「同じ道・同じ曲がり方」なら、路面に合っている VLM の線を使う。
別の道へ引いている・曲がる向きが違う・足元から始まらないなら、投影線を使う。
"""
from __future__ import annotations

import math

XY = tuple[float, float]

MIN_POINTS = 3
START_Y_MIN = 0.75  # VLM の線は足元（画面下）から始まること
TURN_SHIFT_MIN = 0.08  # 左右折なら終点が始点よりこれ以上その側にあること
MEAN_DEV_MAX = 0.08  # VLM の線の各点から案内線までの距離（正規化座標）の平均
MAX_DEV_MAX = 0.18  # 同じく最大
SAMPLES = 24


def _resample(path: list[XY], n: int = SAMPLES) -> list[XY]:
    seg = [math.dist(a, b) for a, b in zip(path, path[1:])]
    total = sum(seg)
    if total <= 0:
        return [path[0]] * n
    out: list[XY] = []
    for k in range(n):
        s, i = total * k / (n - 1), 0
        while i < len(seg) - 1 and s > seg[i]:
            s -= seg[i]
            i += 1
        t = 0.0 if seg[i] <= 0 else min(1.0, s / seg[i])
        a, b = path[i], path[i + 1]
        out.append((a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t))
    return out


def _dist_to_polyline(q: XY, path: list[XY]) -> float:
    best = math.inf
    for a, b in zip(path, path[1:]):
        dx, dy = b[0] - a[0], b[1] - a[1]
        L = dx * dx + dy * dy
        t = 0.0 if L == 0 else max(0.0, min(1.0, ((q[0] - a[0]) * dx + (q[1] - a[1]) * dy) / L))
        best = min(best, math.dist(q, (a[0] + dx * t, a[1] + dy * t)))
    return best


def deviation(vlm: list[XY], geo: list[XY]) -> tuple[float, float]:
    """(平均, 最大)。VLM の線の各点から案内線までの距離。"""
    ds = [_dist_to_polyline(q, geo) for q in _resample(vlm)]
    return sum(ds) / len(ds), max(ds)


def consistent(vlm: list[XY], geo: list[XY], turn: str) -> bool:
    """VLM の線が案内線と同じ道を同じ曲がり方で通っているか。"""
    if len(vlm) < MIN_POINTS or len(geo) < 2 or vlm[0][1] < START_Y_MIN:
        return False
    shift = vlm[-1][0] - vlm[0][0]
    if turn == "left" and shift > -TURN_SHIFT_MIN:
        return False
    if turn == "right" and shift < TURN_SHIFT_MIN:
        return False
    mean, worst = deviation(vlm, geo)
    return mean <= MEAN_DEV_MAX and worst <= MAX_DEV_MAX

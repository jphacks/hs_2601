"""ステップ 8: 採用画像に曲線の矢印を重ね、arrow_image を埋める。

経路は VLM が返した arrow_path（採用候補の score に入っている）を使い、無ければ turn ごとの既定形。
作成者の写真（image_source == creator_photo）には描かず、写真をそのまま使う。
元の Exploration は変更せず、新しいものを返す。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from app.imaging.arrow import default_path, draw_arrow
from app.schemas.exploration import Exploration, ExplorationPoint


@dataclass(frozen=True)
class ArrowStats:
    drawn: list[int] = field(default_factory=list)
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


def arrow_path_for(p: ExplorationPoint) -> tuple[list[tuple[float, float]], bool]:
    """(経路, VLM の経路を使ったか)"""
    if p.chosen_candidate is not None and p.candidates:
        sc = p.candidates[p.chosen_candidate].score
        if sc and len(sc.arrow_path) >= 2:
            return ensure_turn_side([(a.x, a.y) for a in sc.arrow_path], p.turn), True
    return default_path(p.turn), False


def draw_point_arrow(p: ExplorationPoint, out_dir: Path) -> tuple[ExplorationPoint, bool]:
    assert p.image
    path, from_vlm = arrow_path_for(p)
    src = (out_dir / p.image).read_bytes()
    rel = f"images/{p.index:03d}_arrow.jpg"
    (out_dir / rel).write_bytes(draw_arrow(src, path, p.turn))
    return p.model_copy(update={"arrow_image": rel}), from_vlm


def draw_arrows(e: Exploration, out_dir: Path) -> tuple[Exploration, ArrowStats]:
    drawn: list[int] = []
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
        q, from_vlm = draw_point_arrow(p, out_dir)
        drawn.append(p.index)
        if from_vlm:
            with_vlm.append(p.index)
        points.append(q)
    return e.model_copy(update={"points": points}), ArrowStats(drawn, with_vlm, skipped, creator)

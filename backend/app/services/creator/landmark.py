"""ステップ 7: VLM が候補画像を採点し、最良の 1 枚を選んで目印の文章を付ける。

- 候補が無い地点（Street View なし）や VLM が失敗した地点は、案内文と距離からフォールバック文を作る。
- 同じ画像・同じプロンプト・同じモデルの結果はキャッシュし、再実行で API を叩かない。
- 元の Exploration は変更せず、新しいものを返す。
"""
from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass, field
from pathlib import Path

from app.external.vlm.base import Evaluation, VlmClient, VlmError
from app.schemas.exploration import ArrowPoint, Exploration, ExplorationPoint, VlmScore
from app.services.creator.cache import FileCache, cache_key

log = logging.getLogger(__name__)

PROMPT_PATH = Path(__file__).resolve().parents[2] / "external" / "vlm" / "prompts" / "evaluate.txt"
TURN_LABEL = {"left": "左折", "right": "右折", "straight": "直進", "arrive": "到着"}


@dataclass(frozen=True)
class LandmarkStats:
    evaluated: list[int] = field(default_factory=list)
    fallback: list[int] = field(default_factory=list)  # VLM を使えず文章だけ
    errors: dict[int, str] = field(default_factory=dict)


def fallback_text(p: ExplorationPoint) -> str:
    """VLM 不可時の案内文。Routes API の案内文があればそれ、無ければ方向と距離だけ。"""
    if p.turn == "arrive":
        return "目的地です"
    base = p.instruction.strip() if p.instruction else TURN_LABEL[p.turn]
    return f"{base}（次まで {p.distance_to_next_m} m）"


def pano_groups(p: ExplorationPoint) -> str:
    """同じ撮影地点（pano_id）の候補番号をまとめた説明文。例: 「画像 0,1,2,5,7 / 画像 3,4 / 画像 6」"""
    groups: dict[str, list[int]] = {}
    for i, c in enumerate(p.candidates):
        groups.setdefault(c.street_view.pano_id, []).append(i)
    return " / ".join("画像 " + ",".join(map(str, idx)) for idx in groups.values()) or "なし"


def build_prompt(p: ExplorationPoint, n: int, template: str | None = None) -> str:
    tpl = template or PROMPT_PATH.read_text(encoding="utf-8")
    return tpl.format(n=n, turn_label=TURN_LABEL[p.turn], instruction=p.instruction or "（案内文なし）",
                      distance_m=p.distance_to_next_m, groups=pano_groups(p))


def _evaluate_point(client: VlmClient, p: ExplorationPoint, out_dir: Path, cache: FileCache | None) -> Evaluation | None:
    images = [(out_dir / c.image).read_bytes() for c in p.candidates]
    prompt = build_prompt(p, len(images))
    digests = [hashlib.sha256(b).hexdigest()[:16] for b in images]
    key = cache_key("vlm", client.model, prompt, digests)
    cached = cache.get_json(key) if cache else None
    if cached is not None:
        from app.external.vlm.base import parse_evaluation
        return parse_evaluation(cached["raw_text"], len(images))
    ev = client.evaluate(prompt, images)
    if cache:
        cache.set_json(key, {"raw_text": ev.raw_text})
    return ev


def choose_best(cands: list, model_best: int) -> int:
    """立てる候補の中から選ぶ。モデルの選択が立てる候補ならそれを尊重し、そうでなければ点数で選び直す。"""
    scored = [(i, c.score) for i, c in enumerate(cands) if c.score is not None]
    walkable = [(i, sc) for i, sc in scored if sc.on_walkway] or scored
    if any(i == model_best for i, _ in walkable):
        return model_best
    return max(walkable, key=lambda t: (t[1].here + t[1].arrow, t[1].arrow))[0]


def apply_evaluation(p: ExplorationPoint, ev: Evaluation) -> ExplorationPoint:
    by_index = {e.index: e for e in ev.evaluations}
    # 「立てるか」「進めるか」は向きではなく撮影地点の性質。同じパノラマの候補が 1 枚でも該当すれば全部除外する
    bad_panos = {
        p.candidates[e.index].street_view.pano_id
        for e in ev.evaluations if (not e.on_walkway or e.path_blocked) and e.index < len(p.candidates)
    }
    cands = [
        c.model_copy(update={"score": VlmScore(
            on_walkway=e.on_walkway and c.street_view.pano_id not in bad_panos,
            path_blocked=e.path_blocked or c.street_view.pano_id in bad_panos,
            here=e.here, arrow=e.arrow, landmark_text=e.landmark_text, reason=e.reason,
            arrow_path=[ArrowPoint(x=x, y=y) for x, y in e.arrow_path])})
        if (e := by_index.get(i)) else c
        for i, c in enumerate(p.candidates)
    ]
    best_index = choose_best(cands, ev.best_index)
    best = cands[best_index]
    text = best.score.landmark_text if best.score and best.score.landmark_text and best.score.landmark_text != "目印なし" else None
    return p.model_copy(update={
        "candidates": cands, "chosen_candidate": best_index,
        "image": best.image, "street_view": best.street_view,
        "landmark": text or fallback_text(p),
    })


def evaluate_landmarks(client: VlmClient | None, e: Exploration, out_dir: Path, cache: FileCache | None = None) -> tuple[Exploration, LandmarkStats]:
    evaluated: list[int] = []
    fallback: list[int] = []
    errors: dict[int, str] = {}
    points: list[ExplorationPoint] = []
    for p in e.points:
        if client is None or not p.candidates:
            fallback.append(p.index)
            points.append(p.model_copy(update={"landmark": p.landmark or fallback_text(p)}))
            continue
        try:
            ev = _evaluate_point(client, p, out_dir, cache)
            points.append(apply_evaluation(p, ev))
            evaluated.append(p.index)
        except VlmError as err:
            log.warning("point %d: VLM failed: %s", p.index, err)
            errors[p.index] = str(err)
            fallback.append(p.index)
            points.append(p.model_copy(update={"landmark": p.landmark or fallback_text(p)}))
    return e.model_copy(update={"points": points}), LandmarkStats(evaluated, fallback, errors)

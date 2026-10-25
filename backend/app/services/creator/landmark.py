"""ステップ 7: VLM が候補画像を採点し、最良の 1 枚を選んで目印の文章を付ける。

- 候補が無い地点（Street View なし）や VLM が失敗した地点は、案内文と距離からフォールバック文を作る。
- 作成者の写真（image_source == creator_photo）は VLM を呼ばない。caption があればそれ、無ければフォールバック文。
- 同じ画像・同じプロンプト・同じモデルの結果はキャッシュし、再実行で API を叩かない。
- 元の Exploration は変更せず、新しいものを返す。
"""
from __future__ import annotations

import hashlib
import logging
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path

from app.external.vlm.base import Evaluation, VlmClient, VlmError
from app.schemas.exploration import ArrowPoint, Exploration, ExplorationPoint, VlmScore
from app.imaging.guide import draw_guide
from app.services.creator.arrow_geo import geo_arrow_path, geo_visibility, projected_corner
from app.services.creator.cache import FileCache, cache_key
from app.services.creator.geo import LatLngT
from app.services.creator.route import decode_polyline
from app.services.creator.vlm_context import candidate_context, route_context

log = logging.getLogger(__name__)

PROMPT_PATH = Path(__file__).resolve().parents[2] / "external" / "vlm" / "prompts" / "evaluate.txt"
TURN_LABEL = {"left": "左折", "right": "右折", "straight": "直進", "arrive": "到着"}
VLM_WORKERS = 4  # 地点ごとの VLM 評価を並列に投げる数（1 地点 15〜25 秒かかるため）


@dataclass(frozen=True)
class LandmarkStats:
    evaluated: list[int] = field(default_factory=list)
    fallback: list[int] = field(default_factory=list)  # VLM を使えず文章だけ
    errors: dict[int, str] = field(default_factory=dict)
    creator: list[int] = field(default_factory=list)  # 作成者の写真（VLM を呼ばない）


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


def build_prompt(p: ExplorationPoint, n: int, template: str | None = None, route: list[LatLngT] | None = None) -> str:
    """プロンプト。画像だけでなく、経路情報と各候補の撮影位置・向き・経路の投影線を文章で添える。"""
    tpl = template or PROMPT_PATH.read_text(encoding="utf-8")
    return tpl.format(n=n, turn_label=TURN_LABEL[p.turn], instruction=p.instruction or "（案内文なし）",
                      distance_m=p.distance_to_next_m, groups=pano_groups(p),
                      route_info=route_context(p, route), images_info=candidate_context(p, p.candidates[:n], route))


def _evaluate_point(client: VlmClient, p: ExplorationPoint, out_dir: Path, cache: FileCache | None,
                    route: list[LatLngT] | None = None) -> Evaluation | None:
    images = [_vlm_image(out_dir, c, p, route) for c in p.candidates]
    prompt = build_prompt(p, len(images), route=route)
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


def _vlm_image(out_dir: Path, c, p: ExplorationPoint, route: list[LatLngT] | None) -> bytes:
    """VLM に渡す画像。経路があれば、地図の経路を投影した案内線（水色）と曲がる地点の丸を重ねる。"""
    raw = (out_dir / c.image).read_bytes()
    if not route or len(route) < 2:
        return raw
    guide = geo_arrow_path(route, p, c.street_view)
    corner = projected_corner(route, p, c.street_view) if p.turn != "straight" else None
    if not (guide or corner):
        return raw
    try:
        return draw_guide(raw, guide or [], corner)
    except OSError as err:  # 画像として読めない（壊れた JPEG など）なら案内線なしで渡す
        log.warning("point %d: 案内線を重ねられません: %s", p.index, err)
        return raw


def geo_rank(cands: list, p: ExplorationPoint, route: list[LatLngT] | None) -> dict[int, tuple[bool, bool, bool, bool]]:
    """候補ごとの (経路が見える, 公式撮影, 曲がり角まで見える, 足元から始まる)。経路が無ければ全部 True 扱い。"""
    if not route:
        return {i: (True, True, True, True) for i in range(len(cands))}
    return {i: geo_visibility(route, p, c.street_view).rank for i, c in enumerate(cands)}


def choose_best(cands: list, model_best: int, p: ExplorationPoint | None = None, route: list[LatLngT] | None = None) -> int:
    """立てる候補の中から選ぶ。経路（道なり）が曲がり角まで画像に見える候補を優先し、
    その中でモデルの選択があればそれを尊重し、無ければ点数で選び直す。"""
    scored = [(i, c.score) for i, c in enumerate(cands) if c.score is not None]
    # 正面に道が続く候補 → 立てる候補 → 全部、の順に絞る（ルールに反する画像は他に無いときだけ）
    walkable = ([(i, sc) for i, sc in scored if sc.on_walkway and sc.road_ahead]
                or [(i, sc) for i, sc in scored if sc.on_walkway] or scored)
    if p is not None:
        rank = geo_rank(cands, p, route)
        top = max(rank[i] for i, _ in walkable)  # (見える, 公式, 曲がり角まで, 足元から) の最良
        walkable = [(i, sc) for i, sc in walkable if rank[i] == top]
    if any(i == model_best for i, _ in walkable):
        return model_best
    return max(walkable, key=lambda t: (t[1].here + t[1].arrow, t[1].arrow))[0]


def apply_evaluation(p: ExplorationPoint, ev: Evaluation, route: list[LatLngT] | None = None) -> ExplorationPoint:
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
            road_ahead=e.road_ahead,
            here=e.here, arrow=e.arrow, landmark_text=e.landmark_text, reason=e.reason,
            arrow_path=[ArrowPoint(x=x, y=y) for x, y in e.arrow_path])})
        if (e := by_index.get(i)) else c
        for i, c in enumerate(p.candidates)
    ]
    best_index = choose_best(cands, ev.best_index, p, route)
    best = cands[best_index]
    text = best.score.landmark_text if best.score and best.score.landmark_text and best.score.landmark_text != "目印なし" else None
    return p.model_copy(update={
        "candidates": cands, "chosen_candidate": best_index,
        "image": best.image, "street_view": best.street_view,
        "landmark": text or fallback_text(p),
    })


def evaluate_landmarks(client: VlmClient | None, e: Exploration, out_dir: Path, cache: FileCache | None = None) -> tuple[Exploration, LandmarkStats]:
    route = decode_polyline(e.polyline)
    evaluated: list[int] = []
    fallback: list[int] = []
    errors: dict[int, str] = {}
    creator: list[int] = []
    targets = [p for p in e.points if p.image_source != "creator_photo" and client is not None and p.candidates]

    def run(p: ExplorationPoint) -> Evaluation | VlmError:
        try:
            return _evaluate_point(client, p, out_dir, cache, route)
        except VlmError as err:
            return err

    with ThreadPoolExecutor(max_workers=VLM_WORKERS) as pool:
        results = dict(zip((p.index for p in targets), pool.map(run, targets)))

    points: list[ExplorationPoint] = []
    for p in e.points:
        if p.image_source == "creator_photo":
            creator.append(p.index)
            points.append(p.model_copy(update={"landmark": p.landmark or fallback_text(p)}))
            continue
        res = results.get(p.index)
        if isinstance(res, Evaluation):
            points.append(apply_evaluation(p, res, route))
            evaluated.append(p.index)
            continue
        if isinstance(res, VlmError):
            log.warning("point %d: VLM failed: %s", p.index, res)
            errors[p.index] = str(res)
        fallback.append(p.index)
        points.append(p.model_copy(update={"landmark": p.landmark or fallback_text(p)}))
    return e.model_copy(update={"points": points}), LandmarkStats(evaluated, fallback, errors, creator)

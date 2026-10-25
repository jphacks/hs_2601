"""VLM クライアントの共通インターフェース。Gemini / Claude を差し替え可能にする。"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Protocol


class VlmError(RuntimeError):
    """キー・権限・レート制限超過など、VLM 呼び出しの失敗。"""


@dataclass(frozen=True)
class CandidateEvaluation:
    index: int
    on_walkway: bool  # 撮影地点に歩行者が立てるか
    path_blocked: bool  # 進む先の路面へ歩いて行けない（柵・段差・水面）
    here: int  # 1〜5 現在地のわかりやすさ
    arrow: int  # 1〜5 矢印の引きやすさ
    landmark_text: str
    reason: str
    arrow_path: list[tuple[float, float]]  # 0〜1 の正規化座標
    road_ahead: bool = True  # 正面に今歩いている道の路面が手前から奥へ続いて見える（壁・建物・別の道を向いていない）


@dataclass(frozen=True)
class Evaluation:
    evaluations: list[CandidateEvaluation]
    best_index: int
    raw_text: str


class VlmClient(Protocol):
    model: str

    def evaluate(self, prompt: str, images: list[bytes]) -> Evaluation:
        """複数画像を渡し、候補ごとの採点と最良の番号を JSON で受け取る。"""
        ...


def parse_evaluation(text: str, n_images: int) -> Evaluation:
    """モデルの返答（JSON、または ```json ... ``` 付き）を解釈する。"""
    cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", text.strip(), flags=re.S)
    try:
        body = json.loads(cleaned)
    except json.JSONDecodeError as e:
        raise VlmError(f"VLM の返答が JSON ではありません: {text[:200]}") from e
    evals: list[CandidateEvaluation] = []
    for item in body.get("evaluations", []):
        idx = int(item.get("index", -1))
        if not 0 <= idx < n_images:
            continue
        path: list[tuple[float, float]] = []
        for pt in item.get("arrow_path", []) or []:
            try:
                x, y = float(pt["x"]), float(pt["y"])
            except (KeyError, TypeError, ValueError):
                continue
            path.append((min(1.0, max(0.0, x)), min(1.0, max(0.0, y))))
        evals.append(CandidateEvaluation(
            index=idx,
            on_walkway=_as_bool(item.get("on_walkway", True)),
            path_blocked=_as_bool(item.get("path_blocked", False)),
            here=max(1, min(5, int(item.get("here_score", 1)))),
            arrow=max(1, min(5, int(item.get("arrow_score", 1)))),
            landmark_text=str(item.get("landmark", "")).strip(),
            reason=str(item.get("reason", "")).strip(),
            arrow_path=path,
            road_ahead=_as_bool(item.get("road_ahead", True)),
        ))
    if not evals:
        raise VlmError(f"VLM の返答に評価が含まれていません: {text[:200]}")
    best = int(body.get("best_index", -1))
    walkable = ([e for e in evals if e.on_walkway and not e.path_blocked and e.road_ahead]
                or [e for e in evals if e.on_walkway and not e.path_blocked] or evals)  # 使える候補が無ければ全体から選ぶ
    allowed = {e.index for e in walkable}
    if best not in allowed:  # 範囲外、または立てない候補を選んでいたら選び直す
        best = max(walkable, key=lambda e: (e.here + e.arrow, e.arrow)).index
    return Evaluation(evaluations=evals, best_index=best, raw_text=text)


def _as_bool(v: object) -> bool:
    if isinstance(v, bool):
        return v
    return str(v).strip().lower() in ("true", "1", "yes")

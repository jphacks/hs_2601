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
    landmark: int  # 1〜5
    turn: int  # 1〜5
    view: int  # 1〜5 人の視点に近いか
    landmark_text: str
    reason: str


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
        evals.append(CandidateEvaluation(
            index=idx,
            landmark=max(1, min(5, int(item.get("landmark_score", 1)))),
            turn=max(1, min(5, int(item.get("turn_score", 1)))),
            view=max(1, min(5, int(item.get("view_score", 3)))),
            landmark_text=str(item.get("landmark", "")).strip(),
            reason=str(item.get("reason", "")).strip(),
        ))
    if not evals:
        raise VlmError(f"VLM の返答に評価が含まれていません: {text[:200]}")
    best = int(body.get("best_index", -1))
    if not 0 <= best < n_images:
        best = max(evals, key=lambda e: (e.landmark + e.turn + e.view, e.turn)).index
    return Evaluation(evaluations=evals, best_index=best, raw_text=text)

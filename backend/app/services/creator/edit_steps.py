"""下書きの写真列から地点（写真）を選んで外す。公開中の道案内は変えない。

- 外した地点の「次まで」の距離は、直前に残る地点へ足す（歩く距離は変わらない）。
- ゴール（最後の地点）は外せない。外すと道案内として終わらなくなるため。
- 残った地点の index は 0 から振り直す。ストレージの画像は消さない（公開中の画像を誤って消さないため）。
- 元の RoutePlan は変更せず、新しいものを返す。
"""
from __future__ import annotations

from app.schemas.route_plan import RoutePlan, RouteStep


class StepEditError(ValueError):
    """利用者に返す日本語の理由を持つ。"""


def remove_steps(plan: RoutePlan, indices: list[int]) -> RoutePlan:
    """plan.steps の並び順の番号（0 始まり）で指定した地点を外す。"""
    n = len(plan.steps)
    targets = set(indices)
    if not targets:
        raise StepEditError("外す写真を選んでください。")
    if any(i < 0 or i >= n for i in targets):
        raise StepEditError("存在しない写真が指定されています。画面を読み込み直してください。")
    if n - 1 in targets:
        raise StepEditError("ゴールの写真は外せません。")
    kept: list[RouteStep] = []
    for i, step in enumerate(plan.steps):
        if i in targets:
            if kept:  # 外した地点までの距離を直前の地点に足す（先頭を外したときは足し先が無い）
                prev = kept[-1]
                kept[-1] = prev.model_copy(update={"distance_to_next_m": prev.distance_to_next_m + step.distance_to_next_m})
            continue
        kept.append(step)
    renumbered = [s.model_copy(update={"index": k}) for k, s in enumerate(kept)]
    return plan.model_copy(update={"steps": renumbered})

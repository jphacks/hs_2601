"""案内文の整形（純関数）。

Routes API の案内文は「東に進む」「北西に進んで○○に向かう」のように方角で始まるが、
参加者に方角は伝わりにくいので、その地点の turn に合わせて左右・直進で言い換える。
"""
from __future__ import annotations

import re

from app.schemas.exploration import Turn

# 「北東方向に進んで」「南へ進む」「西に向かって進み」などに一致
_COMPASS = re.compile(r"(北東|北西|南東|南西|北|南|東|西)(?:方向|方角)?(?:に|へ)(?:向かって)?進(む|んで|み)")

_HEAD = {"left": "左に進", "right": "右に進", "straight": "直進", "arrive": "直進"}


def normalize_instruction(text: str, turn: Turn) -> str:
    """方角の表現を turn に基づく左右・直進に置き換える。該当が無ければそのまま返す。"""
    if not text:
        return text
    head = _HEAD[turn]

    def repl(m: re.Match[str]) -> str:
        suffix = m.group(2)  # む / んで / み
        if head == "直進":
            return {"む": "直進する", "んで": "直進して", "み": "直進し"}[suffix]
        return head + suffix

    return _COMPASS.sub(repl, text)

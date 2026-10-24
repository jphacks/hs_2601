"""Gemini API（Google AI Studio）クライアント。REST を直接叩く（SDK 不要）。

無料枠は 1 分あたりの回数に上限があるので、429 のときは待って再試行する。
API: https://ai.google.dev/api/generate-content
"""
from __future__ import annotations

import base64
import time

import httpx

from app.external.vlm.base import Evaluation, VlmError, parse_evaluation

GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"

RESPONSE_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "evaluations": {
            "type": "ARRAY",
            "items": {
                "type": "OBJECT",
                "properties": {
                    "index": {"type": "INTEGER"},
                    "landmark_score": {"type": "INTEGER"},
                    "turn_score": {"type": "INTEGER"},
                    "view_score": {"type": "INTEGER"},
                    "landmark": {"type": "STRING"},
                    "reason": {"type": "STRING"},
                },
                "required": ["index", "landmark_score", "turn_score", "view_score", "landmark", "reason"],
            },
        },
        "best_index": {"type": "INTEGER"},
    },
    "required": ["evaluations", "best_index"],
}


class GeminiClient:
    def __init__(self, api_key: str, model: str = "gemini-2.5-flash-lite", http: httpx.Client | None = None,
                 max_retries: int = 3, min_interval_s: float = 0.0) -> None:
        self._api_key = api_key
        self.model = model
        self._http = http or httpx.Client(timeout=60.0)
        self._max_retries = max_retries
        self._min_interval_s = min_interval_s
        self._last_call = 0.0

    def evaluate(self, prompt: str, images: list[bytes]) -> Evaluation:
        parts: list[dict] = [{"text": prompt}]
        for img in images:
            parts.append({"inline_data": {"mime_type": "image/jpeg", "data": base64.b64encode(img).decode()}})
        body = {
            "contents": [{"parts": parts}],
            "generationConfig": {"temperature": 0.2, "response_mime_type": "application/json", "response_schema": RESPONSE_SCHEMA},
        }
        text = self._call(body)
        return parse_evaluation(text, len(images))

    def _call(self, body: dict) -> str:
        url = GEMINI_URL.format(model=self.model)
        for attempt in range(self._max_retries + 1):
            wait = self._min_interval_s - (time.monotonic() - self._last_call)
            if wait > 0:
                time.sleep(wait)
            res = self._http.post(url, params={"key": self._api_key}, json=body)
            self._last_call = time.monotonic()
            if res.status_code == 429 and attempt < self._max_retries:
                time.sleep(2.0 * (attempt + 1) ** 2)  # 2, 8, 18 秒
                continue
            if res.status_code != 200:
                raise VlmError(f"Gemini API failed: HTTP {res.status_code} {res.text[:300]}")
            data = res.json()
            try:
                return data["candidates"][0]["content"]["parts"][0]["text"]
            except (KeyError, IndexError) as e:
                raise VlmError(f"Gemini の返答形式が想定外です: {str(data)[:300]}") from e
        raise VlmError("Gemini API: レート制限の再試行回数を超えました")

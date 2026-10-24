"""Claude API クライアント。REST を直接叩く（SDK 不要）。
API: https://docs.anthropic.com/en/api/messages
"""
from __future__ import annotations

import base64

import httpx

from app.external.vlm.base import Evaluation, VlmError, parse_evaluation

CLAUDE_URL = "https://api.anthropic.com/v1/messages"


class ClaudeClient:
    def __init__(self, api_key: str, model: str = "claude-haiku-4-5", http: httpx.Client | None = None) -> None:
        self._api_key = api_key
        self.model = model
        self._http = http or httpx.Client(timeout=60.0)

    def evaluate(self, prompt: str, images: list[bytes]) -> Evaluation:
        content: list[dict] = []
        for i, img in enumerate(images):
            content.append({"type": "text", "text": f"画像 {i}:"})
            content.append({"type": "image", "source": {"type": "base64", "media_type": "image/jpeg",
                                                        "data": base64.b64encode(img).decode()}})
        content.append({"type": "text", "text": prompt + "\n\nJSON だけを出力してください。"})
        body = {"model": self.model, "max_tokens": 1024, "temperature": 0.2,
                "messages": [{"role": "user", "content": content}]}
        headers = {"x-api-key": self._api_key, "anthropic-version": "2023-06-01", "content-type": "application/json"}
        res = self._http.post(CLAUDE_URL, json=body, headers=headers)
        if res.status_code != 200:
            raise VlmError(f"Claude API failed: HTTP {res.status_code} {res.text[:300]}")
        data = res.json()
        text = "".join(block.get("text", "") for block in data.get("content", []) if block.get("type") == "text")
        return parse_evaluation(text, len(images))

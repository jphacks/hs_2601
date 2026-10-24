"""設定（.env）から VLM クライアントを作る。"""
from __future__ import annotations

from app.core.config import Settings
from app.external.vlm.base import VlmClient, VlmError
from app.external.vlm.claude import ClaudeClient
from app.external.vlm.gemini import GeminiClient


def make_vlm_client(settings: Settings) -> VlmClient:
    provider = settings.vlm_provider.lower()
    if provider == "gemini":
        if not settings.gemini_api_key:
            raise VlmError("GEMINI_API_KEY が未設定です。backend/.env に書いてください（Google AI Studio で発行）。")
        model = settings.vlm_model or "gemini-3.5-flash-lite"
        return GeminiClient(settings.gemini_api_key, model=model, min_interval_s=settings.vlm_min_interval_s)
    if provider == "claude":
        if not settings.anthropic_api_key:
            raise VlmError("ANTHROPIC_API_KEY が未設定です。backend/.env に書いてください。")
        model = settings.vlm_model if settings.vlm_model.startswith("claude") else "claude-haiku-4-5"
        return ClaudeClient(settings.anthropic_api_key, model=model)
    raise VlmError(f"VLM_PROVIDER が不正です: {settings.vlm_provider}（gemini | claude）")

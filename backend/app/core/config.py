"""環境変数の読み込み。

``backend/.env`` があればそこから、なければ OS の環境変数から読む。
使う側は ``get_settings()`` を呼ぶ。テストでは ``get_settings.cache_clear()`` で再読込できる。
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=BACKEND_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # 外部 API キー。未設定なら None（該当機能を呼んだ時点でエラーにする）
    google_maps_api_key: str | None = None
    # VLM（ステップ 7）。Gemini を既定にし、Claude は任意
    gemini_api_key: str | None = None  # Google AI Studio のキー（Maps のキーとは別物）
    anthropic_api_key: str | None = None
    vlm_provider: str = "gemini"  # "gemini" | "claude"
    vlm_model: str = "gemini-3.5-flash"  # claude なら "claude-haiku-4-5" など
    vlm_min_interval_s: float = 4.0  # 無料枠の 1 分あたり上限を超えないための呼び出し間隔

    # 経路探索の出力先（scripts/explore_route.py の --out 既定値）
    out_dir: Path = BACKEND_DIR / "out"
    # 外部 API のレスポンスキャッシュ（同じ入力なら API を叩かない）
    cache_dir: Path = BACKEND_DIR / ".cache"

    def require_google_maps_api_key(self) -> str:
        if not self.google_maps_api_key:
            raise RuntimeError(
                "GOOGLE_MAPS_API_KEY が未設定です。backend/.env に書くか環境変数で渡してください。"
            )
        return self.google_maps_api_key


@lru_cache
def get_settings() -> Settings:
    return Settings()

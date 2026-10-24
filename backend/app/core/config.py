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
    anthropic_api_key: str | None = None

    # 経路探索の出力先（scripts/explore_route.py の --out 既定値）
    out_dir: Path = BACKEND_DIR / "out"

    def require_google_maps_api_key(self) -> str:
        if not self.google_maps_api_key:
            raise RuntimeError(
                "GOOGLE_MAPS_API_KEY が未設定です。backend/.env に書くか環境変数で渡してください。"
            )
        return self.google_maps_api_key


@lru_cache
def get_settings() -> Settings:
    return Settings()

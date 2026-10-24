"""core/config.py が環境変数を読めることを確認する。"""
import pytest

from app.core.config import Settings, get_settings


def test_環境変数から読む(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GOOGLE_MAPS_API_KEY", "dummy-key")
    s = Settings(_env_file=None)
    assert s.google_maps_api_key == "dummy-key"
    assert s.require_google_maps_api_key() == "dummy-key"


def test_未設定なら分かりやすいエラー(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("GOOGLE_MAPS_API_KEY", raising=False)
    s = Settings(_env_file=None)
    assert s.google_maps_api_key is None
    with pytest.raises(RuntimeError, match="GOOGLE_MAPS_API_KEY"):
        s.require_google_maps_api_key()


def test_get_settings_はキャッシュされる() -> None:
    get_settings.cache_clear()
    assert get_settings() is get_settings()

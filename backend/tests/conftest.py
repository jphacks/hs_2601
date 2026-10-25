"""テスト共通の設定。"""
import pytest

import app.services.creator.snapshot as snapshot_mod


@pytest.fixture(autouse=True)
def _no_firefox(monkeypatch: pytest.MonkeyPatch) -> None:
    """テストでは Firefox を起動しない（map.png の撮影は何もしない扱い）。"""
    monkeypatch.setattr(snapshot_mod, "firefox_path", lambda: None)

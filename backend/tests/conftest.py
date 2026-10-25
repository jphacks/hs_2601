"""テスト共通の設定。"""
import pytest

import app.services.creator.map_fallback as map_fallback_mod
import app.services.creator.snapshot as snapshot_mod


@pytest.fixture(autouse=True)
def _no_firefox(monkeypatch: pytest.MonkeyPatch) -> None:
    """テストでは Firefox を起動しない（map.png の撮影は何もしない扱い）。"""
    monkeypatch.setattr(snapshot_mod, "firefox_path", lambda: None)


@pytest.fixture(autouse=True)
def _no_map_tiles(monkeypatch: pytest.MonkeyPatch) -> None:
    """テストでは地理院タイルを取りに行かない（背景なしで経路だけ描く）。"""
    monkeypatch.setattr(map_fallback_mod, "gsi_tile_fetcher", lambda cache=None, http=None: (lambda z, x, y: None))

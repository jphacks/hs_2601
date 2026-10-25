"""map.html / contact.html をヘッドレス Firefox で PNG にする（チームに画像で共有する用）。

Firefox が無い環境では何もしない（html をブラウザで開いて確認する）。
"""
from __future__ import annotations

import logging
import shutil
import subprocess
from pathlib import Path

log = logging.getLogger(__name__)

SIZES = {"map": "1200,900", "contact": "1400,2000"}
TIMEOUT_S = 180


def firefox_path() -> str | None:
    return shutil.which("firefox")


def snapshot(out_dir: Path, name: str, size: str | None = None) -> Path | None:
    """out_dir/<name>.html → out_dir/<name>.png。失敗や Firefox 無しなら None。"""
    out_dir = out_dir.resolve()  # file URI には絶対パスが要る
    html = out_dir / f"{name}.html"
    png = out_dir / f"{name}.png"
    firefox = firefox_path()
    if not html.exists() or not firefox:
        return None
    png.unlink(missing_ok=True)  # snap 版 Firefox は /tmp に書けないので出力先の直下に出す
    try:
        subprocess.run(
            [firefox, "--headless", f"--window-size={size or SIZES.get(name, '1200,900')}", "--screenshot", str(png), html.as_uri()],
            check=False, capture_output=True, timeout=TIMEOUT_S,
        )
    except (OSError, subprocess.TimeoutExpired) as err:
        log.warning("%s.png を作れませんでした: %s", name, err)
        return None
    return png if png.exists() else None


def write_map_png(out_dir: Path) -> Path | None:
    """作る人 API 用: 保存のあとに map.png を作る。失敗しても道案内の作成は成功のまま。"""
    png = snapshot(out_dir, "map")
    if png is None:
        log.info("map.png は作りませんでした（Firefox が無いか描画に失敗）: %s", out_dir)
    return png

"""out/map.html をヘッドレス Firefox で PNG にする（チームに画像で共有する用）。

使い方:
  python -m scripts.snapshot_map --out ./out        # out/map.html → out/map.png

Firefox が無い環境では、ブラウザで map.html を開いて確認する。
"""
from __future__ import annotations

import argparse
import shutil
import subprocess
from pathlib import Path

from app.core.config import get_settings


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", type=Path, default=None, help="map.html があるディレクトリ（既定: backend/out）")
    ap.add_argument("--size", default="1200,900", help="幅,高さ")
    args = ap.parse_args()

    out_dir: Path = (args.out or get_settings().out_dir).resolve()
    html = out_dir / "map.html"
    png = out_dir / "map.png"
    if not html.exists():
        raise SystemExit(f"{html} がありません。先に scripts.geocode などで生成してください。")
    firefox = shutil.which("firefox")
    if not firefox:
        raise SystemExit("firefox が見つかりません。ブラウザで map.html を開いて確認してください。")

    # snap 版 Firefox は /tmp に書けないので、出力先は out/ 直下に固定する
    png.unlink(missing_ok=True)
    subprocess.run(
        [firefox, "--headless", f"--window-size={args.size}", "--screenshot", str(png), html.as_uri()],
        check=False, capture_output=True, timeout=120,
    )
    if not png.exists():
        raise SystemExit("スクリーンショットに失敗しました。ブラウザで map.html を開いて確認してください。")
    print(f"保存: {png}")


if __name__ == "__main__":
    main()

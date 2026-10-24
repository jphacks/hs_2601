"""out/ の map.html / contact.html をヘッドレス Firefox で PNG にする（チームに画像で共有する用）。

使い方:
  python -m scripts.snapshot_map --out ./out                 # map.png と contact.png
  python -m scripts.snapshot_map --out ./out --only map      # map.png だけ
  python -m scripts.snapshot_map --out ./out/cases/4

Firefox が無い環境では、ブラウザで html を開いて確認する。
"""
from __future__ import annotations

import argparse
import shutil
import subprocess
from pathlib import Path

from app.core.config import get_settings

SIZES = {"map": "1200,900", "contact": "1400,2000"}


def snapshot(out_dir: Path, name: str, size: str | None = None) -> Path | None:
    """out_dir/<name>.html → out_dir/<name>.png。失敗や Firefox 無しなら None。"""
    out_dir = out_dir.resolve()  # file URI には絶対パスが要る
    html = out_dir / f"{name}.html"
    png = out_dir / f"{name}.png"
    firefox = shutil.which("firefox")
    if not html.exists() or not firefox:
        return None
    png.unlink(missing_ok=True)  # snap 版 Firefox は /tmp に書けないので out/ 直下に出す
    subprocess.run(
        [firefox, "--headless", f"--window-size={size or SIZES.get(name, '1200,900')}", "--screenshot", str(png), html.as_uri()],
        check=False, capture_output=True, timeout=180,
    )
    return png if png.exists() else None


def write_snapshots(out_dir: Path, names: tuple[str, ...] = ("map", "contact")) -> dict[str, Path | None]:
    """html を書き換えた直後に呼び、同名の PNG も更新する。Firefox が無ければ案内だけ出して何もしない。"""
    if not shutil.which("firefox"):
        print("png: firefox が無いので省略（html をブラウザで開いてください）")
        return {name: None for name in names}
    results = {name: snapshot(out_dir, name) for name in names}
    for name, png in results.items():
        print(f"{name}.png: {png if png else '失敗（html が無いか描画エラー）'}")
    return results


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", type=Path, default=None, help="html があるディレクトリ（既定: backend/out）")
    ap.add_argument("--only", choices=["map", "contact"], default=None)
    args = ap.parse_args()

    out_dir: Path = (args.out or get_settings().out_dir).resolve()
    if not shutil.which("firefox"):
        raise SystemExit("firefox が見つかりません。ブラウザで html を開いて確認してください。")
    for name in ([args.only] if args.only else ["map", "contact"]):
        png = snapshot(out_dir, name)
        print(f"{name}: {png if png else '失敗（html が無いか描画エラー）'}")


if __name__ == "__main__":
    main()

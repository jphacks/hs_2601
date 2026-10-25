"""ステップ 8 の確認コマンド: 採用画像に曲線の矢印を描き、arrow_image を route.json に書く。

使い方:
  python -m scripts.arrow --from-route ./out/cases/4

前提: scripts.landmark を実行済み（VLM の arrow_path を使う）。未実行でも turn ごとの既定形で描ける。
出力: images/NNN_arrow.png、route.json（上書き）、contact.html（矢印入り画像を表示）
"""
from __future__ import annotations

import argparse
from pathlib import Path

from app.schemas.exploration import Exploration
from app.services.creator.arrow import draw_arrows
from app.services.creator.contact import TURN_LABEL, render_contact_html
from scripts.snapshot_map import write_snapshots
from scripts.streetview import build_map


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--no-png", action="store_true", help="map.png と contact.png を更新しない")
    ap.add_argument("--from-route", type=Path, required=True)
    ap.add_argument("--source", choices=["geo", "vlm"], default="geo", help="geo: 経路を投影（既定）/ vlm: VLM の点列")
    args = ap.parse_args()
    d: Path = args.from_route
    e = Exploration.model_validate_json((d / "route.json").read_text(encoding="utf-8"))
    e2, stats = draw_arrows(e, d, args.source)
    (d / "route.json").write_text(e2.model_dump_json(indent=2), encoding="utf-8")
    title = f"矢印: {e.origin.query} → {e.destination.query}（描画 {len(stats.drawn)}, うち地図+画像 {len(stats.with_fused_path)} / 投影 {len(stats.with_geo_path)} / VLM {len(stats.with_vlm_path)}, 画像なし {len(stats.skipped)}）"
    (d / "contact.html").write_text(render_contact_html(e2, title), encoding="utf-8")
    (d / "map.html").write_text(build_map(e2, title), encoding="utf-8")
    print(title)
    for p in e2.points:
        src = "投影" if p.index in stats.with_geo_path else "VLM" if p.index in stats.with_vlm_path else "作成者写真" if p.index in stats.creator else ("既定形" if p.arrow_image else "-")
        print(f"  {p.index:2d} {TURN_LABEL[p.turn]:<6} {p.arrow_image or '(画像なし)':<22} {src}")
    print(f"\n一覧: {d / 'contact.html'}")
    if not args.no_png:
        write_snapshots(d)


if __name__ == "__main__":
    main()

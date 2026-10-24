"""ステップ 7 の確認コマンド: VLM が候補画像を採点し、最良の 1 枚と目印の文章を route.json に書く。

使い方:
  python -m scripts.landmark --from-route ./out/cases/4
  python -m scripts.landmark --from-route ./out/cases/4 --no-vlm     # VLM を使わずフォールバック文だけ

前提: scripts.streetview（候補の複数取得）を実行済みで、.env に GEMINI_API_KEY（または ANTHROPIC_API_KEY）がある。
出力: route.json（上書き）、contact.html（採点つき。選ばれた候補を青枠で表示）
"""
from __future__ import annotations

import argparse
import logging
from pathlib import Path

from app.core.config import get_settings
from app.external.vlm.factory import make_vlm_client
from app.schemas.exploration import Exploration
from app.services.creator.cache import FileCache
from app.services.creator.contact import TURN_LABEL, render_contact_html
from app.services.creator.landmark import evaluate_landmarks
from app.services.creator.route import decode_polyline  # noqa: F401
from scripts.streetview import build_map


def main() -> None:
    logging.basicConfig(level=logging.WARNING, format="%(levelname)s %(message)s")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--from-route", type=Path, required=True)
    ap.add_argument("--no-vlm", action="store_true")
    ap.add_argument("--no-cache", action="store_true")
    args = ap.parse_args()

    settings = get_settings()
    d: Path = args.from_route
    e = Exploration.model_validate_json((d / "route.json").read_text(encoding="utf-8"))
    client = None if args.no_vlm else make_vlm_client(settings)
    cache = None if args.no_cache else FileCache(settings.cache_dir, "vlm")
    e2, stats = evaluate_landmarks(client, e, d, cache)

    (d / "route.json").write_text(e2.model_dump_json(indent=2), encoding="utf-8")
    model = client.model if client else "なし"
    title = f"目印: {e.origin.query} → {e.destination.query}（VLM {model}, 評価 {len(stats.evaluated)} / フォールバック {len(stats.fallback)}）"
    (d / "contact.html").write_text(render_contact_html(e2, title), encoding="utf-8")
    (d / "map.html").write_text(build_map(e2, title), encoding="utf-8")

    print(title)
    for p in e2.points:
        chosen = f"候補#{p.chosen_candidate}" if p.chosen_candidate is not None else "候補なし"
        sc = p.candidates[p.chosen_candidate].score if p.chosen_candidate is not None else None
        score = f"目印{sc.landmark}/曲{sc.turn}/矢印{sc.arrow}" if sc else "-"
        print(f"  {p.index:2d} {TURN_LABEL[p.turn]:<6} {chosen:<8} {score:<14} {p.landmark}")
    for i, msg in stats.errors.items():
        print(f"  ! 地点 {i}: {msg}")
    print(f"\n一覧: {d / 'contact.html'}")


if __name__ == "__main__":
    main()

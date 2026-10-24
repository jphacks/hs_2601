"""ステップ 6: 出発地と目的地から、交差点の写真列（route.json + 画像）を一括生成する。

使い方:
  python -m scripts.explore_route "大阪駅" "グランフロント大阪" --out ./out
  python -m scripts.explore_route "大阪駅" "グランフロント大阪" --via "梅田スカイビル" --out ./out
  python -m scripts.explore_route "大阪駅" "グランフロント大阪" --no-cache     # キャッシュを使わず必ず API を叩く

処理: geocode → route → turns → streetview（候補を複数）→ landmark（VLM が採点して 1 枚を選び、目印文と矢印の経路を返す）→ arrow（曲線の矢印を描く）
出力: out/route.json, out/images/, out/raw/, out/map.html, out/contact.html, map.png, contact.png（PNG は --no-png で省略）
キャッシュ: 同じ地名・座標・パノラマ・画像+プロンプトなら backend/.cache/ を再利用する。
VLM のキーが無いときは --no-vlm と同じ（フォールバック文のみ）。
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from app.core.config import get_settings
from app.external.google.geocoding import GeocodingClient
from app.external.google.routes import RoutesClient
from app.external.google.street_view import StreetViewClient
from app.external.vlm.base import VlmError
from app.external.vlm.factory import make_vlm_client
from app.services.creator.cache import FileCache
from app.services.creator.contact import TURN_LABEL, render_contact_html
from app.services.creator.geocode import geocode_queries
from app.services.creator.route import compute_route
from app.services.creator.arrow import draw_arrows
from app.services.creator.landmark import evaluate_landmarks
from app.services.creator.streetview import StreetViewOptions, fetch_candidates
from app.services.creator.turns import extract_turns
from scripts.snapshot_map import write_snapshots
from scripts.streetview import build_map


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("origin")
    ap.add_argument("destination")
    ap.add_argument("--via", action="append", default=[], help="経由地（複数可）")
    ap.add_argument("--out", type=Path, default=None, help="出力先（既定: backend/out）")
    ap.add_argument("--no-cache", action="store_true", help="キャッシュを使わない")
    ap.add_argument("--heading", choices=["approach", "bisector", "departure"], default="bisector")
    ap.add_argument("--fov", type=int, default=90)
    ap.add_argument("--pitch", type=int, default=0)
    ap.add_argument("--offset-m", type=float, default=0.0)
    ap.add_argument("--no-vlm", action="store_true", help="VLM の採点を行わず、フォールバック文だけ付ける")
    ap.add_argument("--no-png", action="store_true", help="map.png と contact.png を出さない（既定は Firefox があれば出す）")
    args = ap.parse_args()

    settings = get_settings()
    key = settings.require_google_maps_api_key()
    out_dir: Path = args.out or settings.out_dir
    (out_dir / "raw").mkdir(parents=True, exist_ok=True)
    cache = None if args.no_cache else FileCache(settings.cache_dir, "google")

    # 2. geocode
    geo = geocode_queries(GeocodingClient(key), [args.origin, *args.via, args.destination], cache)
    origin, dest, via = geo.places[0], geo.places[-1], geo.places[1:-1]
    (out_dir / "raw" / "geocode.json").write_text(json.dumps(geo.raw, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[2/7] geocode: {origin.query} ({origin.lat:.5f},{origin.lng:.5f}) → {dest.query} ({dest.lat:.5f},{dest.lng:.5f})")

    # 3. route
    ro = compute_route(RoutesClient(key), origin, dest, via, cache)
    (out_dir / "raw" / "routes.json").write_text(json.dumps(ro.raw, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[3/7] route: {ro.route.distance_m} m, 約 {ro.route.duration_s // 60} 分, {len(ro.route.steps)} ステップ")

    # 4. turns
    turns = extract_turns(ro.route, origin, dest)
    e = turns.exploration
    print(f"[4/7] turns: 採用 {len(e.points)} / 候補 {len(turns.decisions)}")

    # 5. street view（候補を複数）
    opt = StreetViewOptions(offset_m=args.offset_m, fov=args.fov, pitch=args.pitch, heading_mode=args.heading)
    e, stats = fetch_candidates(StreetViewClient(key), e, out_dir, opt, cache=cache)
    n_cand = sum(len(p.candidates) for p in e.points)
    print(f"[5/7] street view: 地点 {len(stats.fetched)} / なし {len(stats.missing)}, 候補 {n_cand} 枚")

    # 7. VLM が採点して 1 枚を選び、目印文を付ける
    vlm = None
    if not args.no_vlm:
        try:
            vlm = make_vlm_client(settings)
        except VlmError as err:
            print(f"[6/7] VLM なし（{err}）→ フォールバック文のみ")
    e, lstats = evaluate_landmarks(vlm, e, out_dir, None if args.no_cache else FileCache(settings.cache_dir, "vlm"))
    if vlm:
        print(f"[6/7] landmark ({vlm.model}): 評価 {len(lstats.evaluated)} / フォールバック {len(lstats.fallback)}")
        for i, msg in lstats.errors.items():
            print(f"      ! 地点 {i}: {msg}")

    # 8. 矢印
    e, astats = draw_arrows(e, out_dir)
    print(f"[7/7] arrow: 描画 {len(astats.drawn)}（VLM 経路 {len(astats.with_vlm_path)}）/ 画像なし {len(astats.skipped)}")

    title = f"{origin.query} → {dest.query}（{e.total_distance_m} m, {len(e.points)} 地点）"
    (out_dir / "route.json").write_text(e.model_dump_json(indent=2), encoding="utf-8")
    (out_dir / "contact.html").write_text(render_contact_html(e, title), encoding="utf-8")
    (out_dir / "map.html").write_text(build_map(e, title), encoding="utf-8")

    for p in e.points:
        print(f"  {p.index:2d} {TURN_LABEL[p.turn]:<6} 次まで {p.distance_to_next_m:4d} m  候補 {len(p.candidates)}  {p.landmark or ''}")
    print(f"\n一覧: {out_dir / 'contact.html'}\n地図: {out_dir / 'map.html'}")
    if not args.no_png:
        write_snapshots(out_dir)


if __name__ == "__main__":
    main()

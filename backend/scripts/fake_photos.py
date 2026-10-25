"""手順 11: テスト用の作成者写真を Street View で作り、photos.json を出す。

使い方:
  python -m scripts.fake_photos "四天王寺 南大門" "天王寺公園 てんしば" --n 3 --out ./out/cases/6
  python -m scripts.fake_photos "..." "..." --n 3 --out ./out/cases/6 --name "写真つき→てんしば"
出力: <out>/photos/svN.jpg、<out>/photos.json（作成入力。docs/interface.md 4 章）
続き:  python -m scripts.photos_map --input ./out/cases/6
       python -m scripts.explore_route --photos ./out/cases/6 --out ./out/cases/6 --publish
"""
from __future__ import annotations

import argparse
from pathlib import Path

from app.core.config import get_settings
from app.external.google.geocoding import GeocodingClient
from app.external.google.routes import RoutesClient
from app.external.google.street_view import StreetViewClient
from app.services.creator.cache import FileCache
from app.services.creator.fake_photos import make_fake_photos
from app.services.creator.geocode import geocode_queries
from app.services.creator.route import compute_route


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("origin")
    ap.add_argument("destination")
    ap.add_argument("--n", type=int, default=3, help="写真の枚数")
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--name", default=None, help="photos.json の命名（既定: 出発地→目的地（写真 n 枚））")
    ap.add_argument("--no-cache", action="store_true")
    args = ap.parse_args()

    settings = get_settings()
    key = settings.require_google_maps_api_key()
    cache = None if args.no_cache else FileCache(settings.cache_dir, "google")
    geo = geocode_queries(GeocodingClient(key), [args.origin, args.destination], cache)
    origin, dest = geo.places
    ro = compute_route(RoutesClient(key), origin, dest, [], cache)
    name = args.name or f"{origin.query}→{dest.query}（写真 {args.n} 枚）"
    plan, stats = make_fake_photos(StreetViewClient(key), ro.route, origin, dest, args.n, args.out, name, cache)
    print(f"{plan.name}: 写真 {len(plan.photos)} 枚（Street View なし {len(stats.missing)}）")
    for p in plan.photos:
        print(f"  {p.seq} ({p.lat:.5f}, {p.lng:.5f}) {p.image}")
    print(f"\n入力: {args.out / 'photos.json'}")


if __name__ == "__main__":
    main()

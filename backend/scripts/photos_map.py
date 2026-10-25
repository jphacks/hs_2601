"""手順 6: photos.json の写真を撮影順に地図へ出す（経路計算の前の目視確認）。

使い方:
  python -m scripts.photos_map --input ./out/cases/6        # photos.json があるディレクトリ
出力: <dir>/photos_map.html（S = 出発、番号 = 写真、G = 目的地。クリックで写真）
出発地・目的地に座標が無ければ Geocoding で補う（キャッシュあり）。
"""
from __future__ import annotations

import argparse
from pathlib import Path

from app.core.config import get_settings
from app.external.google.geocoding import GeocodingClient
from app.schemas.creator_input import PlaceInput
from app.schemas.exploration import Place
from app.services.creator.cache import FileCache
from app.services.creator.geocode import resolve_places as resolve_place_inputs
from app.services.creator.photos import load_plan_input
from app.services.creator.photos_map import render_photos_map


def resolve_places(places: list[PlaceInput], cache: FileCache | None) -> list[Place]:
    """座標付きはそのまま、無ければ Geocoding（キーは必要になったときだけ読む）。"""
    need = any(p.lat is None for p in places)
    client = GeocodingClient(get_settings().require_google_maps_api_key()) if need else None
    return resolve_place_inputs(places, client, cache)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--input", type=Path, required=True, help="photos.json があるディレクトリ")
    ap.add_argument("--no-cache", action="store_true")
    args = ap.parse_args()
    plan = load_plan_input(args.input)
    cache = None if args.no_cache else FileCache(get_settings().cache_dir, "google")
    origin, dest = resolve_places([plan.origin, plan.destination], cache)
    out = args.input / "photos_map.html"
    out.write_text(render_photos_map(plan, origin, dest), encoding="utf-8")
    print(f"{plan.name}: {origin.query} → {dest.query}, 写真 {len(plan.photos)} 枚")
    for p in plan.photos:
        print(f"  {p.seq} ({p.lat:.5f}, {p.lng:.5f}) {p.image} {p.caption or ''}")
    print(f"\n地図: {out}")


if __name__ == "__main__":
    main()

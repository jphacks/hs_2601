"""ステップ 2 の確認コマンド: 地名を座標にして地図に出す。

使い方:
  python -m scripts.geocode "大阪駅" "グランフロント大阪" --out ./out
  python -m scripts.geocode --fixture tests/fixtures/geocode_sample.json --out ./out   # API キー不要

出力:
  out/geocode.json      座標の一覧（中間形式の Place の配列）
  out/raw/geocode.json  API の生レスポンス
  out/map.html          ブラウザで開いて確認
"""
from __future__ import annotations

import argparse
import html
import json
from pathlib import Path

from app.core.config import get_settings
from app.external.google.geocoding import GeocodingClient
from app.services.creator.geocode import GeocodeOutput, geocode_from_raw, geocode_queries
from app.services.creator.mapview import MapSpec, Marker, render_map_html

COLORS = ["green", "red", "blue", "orange", "purple"]


def build_map(out: GeocodeOutput) -> str:
    markers = [
        Marker(
            lat=p.lat,
            lng=p.lng,
            label=str(i + 1),
            color=COLORS[i % len(COLORS)],
            popup_html=f"<b>{html.escape(p.query)}</b><br>"
            f"{html.escape(out.raw[p.query]['results'][0].get('formatted_address', ''))}<br>"
            f"{p.lat:.6f}, {p.lng:.6f}",
        )
        for i, p in enumerate(out.places)
    ]
    return render_map_html(MapSpec(title="Geocoding 確認", markers=markers, data=[p.model_dump() for p in out.places]))


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("queries", nargs="*", help="地名・住所（複数可）")
    ap.add_argument("--out", type=Path, default=None, help="出力先ディレクトリ（既定: backend/out）")
    ap.add_argument("--fixture", type=Path, default=None, help="API を叩かず、保存済み raw/geocode.json から描画する")
    args = ap.parse_args()

    settings = get_settings()
    out_dir: Path = args.out or settings.out_dir
    (out_dir / "raw").mkdir(parents=True, exist_ok=True)

    if args.fixture:
        result = geocode_from_raw(json.loads(args.fixture.read_text(encoding="utf-8")))
    else:
        if not args.queries:
            ap.error("地名を 1 つ以上指定するか --fixture を使ってください")
        client = GeocodingClient(settings.require_google_maps_api_key())
        result = geocode_queries(client, args.queries)

    (out_dir / "raw" / "geocode.json").write_text(json.dumps(result.raw, ensure_ascii=False, indent=2), encoding="utf-8")
    (out_dir / "geocode.json").write_text(
        json.dumps([p.model_dump() for p in result.places], ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (out_dir / "map.html").write_text(build_map(result), encoding="utf-8")

    for p in result.places:
        print(f"{p.query}: {p.lat:.6f}, {p.lng:.6f}")
    print(f"\n地図: {out_dir / 'map.html'}")


if __name__ == "__main__":
    main()

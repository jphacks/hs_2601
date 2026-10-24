"""ステップ 3 の確認コマンド: 徒歩経路を取って地図に描く。

使い方:
  python -m scripts.route "大阪駅" "グランフロント大阪" --out ./out
  python -m scripts.route "大阪駅" "グランフロント大阪" --via "梅田スカイビル" --out ./out   # 経由地あり
  python -m scripts.route --from-raw ./out --out ./out      # API を叩かず raw/*.json から描画

出力:
  out/raw/geocode.json  Geocoding の生レスポンス
  out/raw/routes.json   Routes API の生レスポンス
  out/route_preview.json  ステップ一覧（確認用の簡易形式。中間形式 route.json はステップ 4 で作る）
  out/map.html          経路線とステップごとのピン
"""
from __future__ import annotations

import argparse
import html
import json
from pathlib import Path

from app.core.config import get_settings
from app.external.google.geocoding import GeocodingClient
from app.external.google.routes import RoutesClient
from app.services.creator.geocode import GeocodeOutput, geocode_from_raw, geocode_queries
from app.services.creator.mapview import MapSpec, Marker, render_map_html
from app.services.creator.route import RouteOutput, compute_route, decode_polyline, route_from_raw

MANEUVER_COLOR = {"left": "orange", "right": "purple"}


def maneuver_color(maneuver: str) -> str:
    m = maneuver.upper()
    if "LEFT" in m:
        return MANEUVER_COLOR["left"]
    if "RIGHT" in m:
        return MANEUVER_COLOR["right"]
    return "blue"


def build_map(geo: GeocodeOutput, ro: RouteOutput) -> str:
    route = ro.route
    markers: list[Marker] = []
    for i, s in enumerate(route.steps):
        markers.append(
            Marker(
                lat=s.start.lat,
                lng=s.start.lng,
                label=str(i),
                color=maneuver_color(s.maneuver),
                popup_html=f"<b>step {i}</b> {html.escape(s.maneuver or '-')}<br>"
                f"{html.escape(s.instruction)}<br>次まで {s.distance_m} m",
            )
        )
    origin, dest = geo.places[0], geo.places[-1]
    markers.append(Marker(lat=origin.lat, lng=origin.lng, label="S", color="green", popup_html=html.escape(origin.query)))
    markers.append(Marker(lat=dest.lat, lng=dest.lng, label="G", color="red", popup_html=html.escape(dest.query)))
    preview = {
        "distance_m": route.distance_m,
        "duration_s": route.duration_s,
        "steps": [
            {"index": i, "lat": s.start.lat, "lng": s.start.lng, "maneuver": s.maneuver,
             "instruction": s.instruction, "distance_m": s.distance_m}
            for i, s in enumerate(route.steps)
        ],
    }
    spec = MapSpec(
        title=f"経路確認: {origin.query} → {dest.query}（{route.distance_m} m, 約 {route.duration_s // 60} 分, {len(route.steps)} ステップ）",
        markers=markers,
        path=decode_polyline(route.polyline),
        data=preview,
    )
    return render_map_html(spec), preview


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("origin", nargs="?", help="出発地")
    ap.add_argument("destination", nargs="?", help="目的地")
    ap.add_argument("--via", action="append", default=[], help="経由地（複数可）")
    ap.add_argument("--out", type=Path, default=None, help="出力先（既定: backend/out）")
    ap.add_argument("--from-raw", type=Path, default=None, help="API を叩かず、この DIR/raw/*.json から描画する")
    args = ap.parse_args()

    settings = get_settings()
    out_dir: Path = args.out or settings.out_dir
    (out_dir / "raw").mkdir(parents=True, exist_ok=True)

    if args.from_raw:
        geo = geocode_from_raw(json.loads((args.from_raw / "raw" / "geocode.json").read_text(encoding="utf-8")))
        ro = route_from_raw(json.loads((args.from_raw / "raw" / "routes.json").read_text(encoding="utf-8")))
    else:
        if not (args.origin and args.destination):
            ap.error("出発地と目的地を指定するか --from-raw を使ってください")
        key = settings.require_google_maps_api_key()
        geo = geocode_queries(GeocodingClient(key), [args.origin, *args.via, args.destination])
        via = geo.places[1:-1]
        ro = compute_route(RoutesClient(key), geo.places[0], geo.places[-1], via)
        (out_dir / "raw" / "geocode.json").write_text(json.dumps(geo.raw, ensure_ascii=False, indent=2), encoding="utf-8")
        (out_dir / "raw" / "routes.json").write_text(json.dumps(ro.raw, ensure_ascii=False, indent=2), encoding="utf-8")

    page, preview = build_map(geo, ro)
    (out_dir / "route_preview.json").write_text(json.dumps(preview, ensure_ascii=False, indent=2), encoding="utf-8")
    (out_dir / "map.html").write_text(page, encoding="utf-8")

    r = ro.route
    print(f"{geo.places[0].query} → {geo.places[-1].query}: {r.distance_m} m, 約 {r.duration_s // 60} 分, {len(r.steps)} ステップ")
    for i, s in enumerate(r.steps):
        print(f"  {i:2d} {s.maneuver or '-':<18} {s.distance_m:4d} m  {s.instruction}")
    print(f"\n地図: {out_dir / 'map.html'}")


if __name__ == "__main__":
    main()

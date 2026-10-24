"""ステップ 5 の確認コマンド: route.json の各点に Street View 画像を付ける。

使い方:
  python -m scripts.streetview --from-route ./out/cases/4            # route.json を読んで画像を埋める
  python -m scripts.streetview --from-route ./out/cases/4 --offset-m 10 --fov 100

出力（--from-route の DIR 内）:
  route.json      image / street_view が埋まる（上書き）
  images/NNN.jpg  画像
  contact.html    画像一覧（ブラウザで開く）
  map.html        ピンをクリックで画像
"""
from __future__ import annotations

import argparse
import html
from pathlib import Path

from app.core.config import get_settings
from app.external.google.street_view import StreetViewClient
from app.schemas.exploration import Exploration
from app.services.creator.contact import TURN_LABEL, render_contact_html
from scripts.snapshot_map import write_snapshots
from app.services.creator.mapview import MapSpec, Marker, render_map_html
from app.services.creator.route import decode_polyline
from app.core.config import get_settings as _gs  # noqa: F401
from app.services.creator.cache import FileCache
from app.services.creator.streetview import StreetViewOptions, fetch_candidates, fetch_images

COLOR = {"left": "orange", "right": "purple", "straight": "blue", "arrive": "red"}


def build_map(e: Exploration, title: str) -> str:
    markers = []
    for p in e.points:
        color = "green" if p.maneuver.upper() == "DEPART" else COLOR[p.turn]
        shown = p.arrow_image or p.image
        img = f'<br><img src="{html.escape(shown)}" width="280">' if shown else "<br>(Street View なし)"
        popup = f"<b>{p.index} {TURN_LABEL[p.turn]}</b> 次まで {p.distance_to_next_m} m<br>{html.escape(p.instruction)}{img}"
        markers.append(Marker(p.lat, p.lng, str(p.index), popup, color))
    return render_map_html(MapSpec(title=title, markers=markers, path=decode_polyline(e.polyline)))


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--no-png", action="store_true", help="map.png と contact.png を更新しない")
    ap.add_argument("--from-route", type=Path, required=True, help="route.json があるディレクトリ")
    ap.add_argument("--offset-m", type=float, default=0.0, help="交差点の何 m 手前から撮るか（既定 0）")
    ap.add_argument("--fov", type=int, default=90)
    ap.add_argument("--pitch", type=int, default=0)
    ap.add_argument("--no-prefer-official", action="store_true", help="Google 公式パノラマの優先をやめ、最寄りをそのまま使う")
    ap.add_argument("--heading", choices=["approach", "bisector", "departure"], default="bisector",
                    help="カメラの向き: approach=進入方向, bisector=進入と退出の中間（既定）, departure=退出方向")
    ap.add_argument("--single", action="store_true", help="候補を複数取らず、--heading の 1 枚だけ取る")
    ap.add_argument("--no-cache", action="store_true")
    args = ap.parse_args()

    d: Path = args.from_route
    e = Exploration.model_validate_json((d / "route.json").read_text(encoding="utf-8"))
    client = StreetViewClient(get_settings().require_google_maps_api_key())
    opt = StreetViewOptions(offset_m=args.offset_m, fov=args.fov, pitch=args.pitch, prefer_official=not args.no_prefer_official, heading_mode=args.heading)
    cache = None if args.no_cache else FileCache(get_settings().cache_dir, "google")
    if args.single:
        e2, stats = fetch_images(client, e, d, opt, cache)
    else:
        e2, stats = fetch_candidates(client, e, d, opt, cache=cache)

    (d / "route.json").write_text(e2.model_dump_json(indent=2), encoding="utf-8")
    n_cand = sum(len(p.candidates) for p in e2.points)
    title = f"Street View: {e.origin.query} → {e.destination.query}（地点 {len(stats.fetched)} / なし {len(stats.missing)}, 候補 {n_cand} 枚, fov {opt.fov}°）"
    (d / "contact.html").write_text(render_contact_html(e2, title), encoding="utf-8")
    (d / "map.html").write_text(build_map(e2, title), encoding="utf-8")

    print(title)
    for p in e2.points:
        if p.image and p.street_view:
            src = "公式" if "google" in (p.street_view.copyright or "").lower() else f"投稿({p.street_view.copyright})"
            sv = f"{p.image}  {p.street_view.date or '日付不明'}  手前{p.street_view.offset_m:.0f}m  {src}"
        else:
            sv = "(なし)"
        cam = p.street_view.heading if p.street_view else (p.heading or 0)
        print(f"  {p.index:2d} {TURN_LABEL[p.turn]:<6} 進入 {p.heading or 0:3.0f}° → カメラ {cam:3.0f}°  候補 {len(p.candidates)} 枚  {sv}")
    print(f"\n一覧: {d / 'contact.html'}\n地図: {d / 'map.html'}")
    if not args.no_png:
        write_snapshots(d)


if __name__ == "__main__":
    main()

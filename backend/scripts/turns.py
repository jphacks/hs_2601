"""ステップ 4 の確認コマンド: 曲がり角を抽出して中間形式 route.json を作り、採用・不採用を地図に出す。

使い方:
  python -m scripts.turns "大阪駅" "グランフロント大阪" --out ./out
  python -m scripts.turns --from-raw ./out --out ./out     # API を叩かず raw/*.json から

出力:
  out/route.json   中間形式（画像はまだ null。ステップ 5 で埋める）
  out/map.html     採用点を turn の色で、不採用点を灰色で表示。クリックで判定理由
"""
from __future__ import annotations

import argparse
import html
import json
from pathlib import Path

from app.core.config import get_settings
from app.external.google.geocoding import GeocodingClient
from app.external.google.routes import RoutesClient
from app.services.creator.geocode import geocode_from_raw, geocode_queries
from app.services.creator.mapview import MapSpec, Marker, render_map_html
from app.services.creator.route import compute_route, decode_polyline, route_from_raw
from app.services.creator.turns import Decision, TurnsOutput, extract_turns

TURN_COLOR = {"left": "orange", "right": "purple", "straight": "blue", "arrive": "red"}


def marker_for(d: Decision, index_label: str) -> Marker:
    c = d.candidate
    fmt = lambda v: "-" if v is None else f"{v:.0f}°"
    detail = (
        f"maneuver: {html.escape(c.maneuver or '-')}<br>"
        f"案内: {html.escape(c.instruction or '-')}<br>"
        f"入 {fmt(c.heading_in)} → 出 {fmt(c.heading_out)}（Δ {fmt(c.delta_deg)}）"
    )
    if d.accepted:
        color = "green" if c.maneuver.upper() == "DEPART" else TURN_COLOR[d.turn or "straight"]
        return Marker(c.lat, c.lng, index_label, f"<b>採用 {index_label}: {d.turn}</b><br>{detail}", color)
    return Marker(c.lat, c.lng, "×", f"<b>不採用: {d.reason}</b><br>{detail}", "gray")


def build_map(title: str, out: TurnsOutput) -> str:
    markers: list[Marker] = []
    n = 0
    for d in out.decisions:
        label = str(n) if d.accepted else "×"
        markers.append(marker_for(d, label))
        if d.accepted:
            n += 1
    # 採用点が上に重なるよう、不採用を先に描く
    markers.sort(key=lambda m: m.color != "gray")
    e = out.exploration
    data = {
        "summary": {"total_distance_m": e.total_distance_m, "accepted": len(e.points), "rejected": len(out.decisions) - len(e.points)},
        "points": [
            {"index": p.index, "turn": p.turn, "maneuver": p.maneuver, "instruction": p.instruction,
             "heading": p.heading, "distance_to_next_m": p.distance_to_next_m}
            for p in e.points
        ],
    }
    return render_map_html(MapSpec(title=title, markers=markers, path=decode_polyline(e.polyline), data=data))


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("origin", nargs="?")
    ap.add_argument("destination", nargs="?")
    ap.add_argument("--via", action="append", default=[])
    ap.add_argument("--out", type=Path, default=None)
    ap.add_argument("--from-raw", type=Path, default=None)
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
        ro = compute_route(RoutesClient(key), geo.places[0], geo.places[-1], geo.places[1:-1])
        (out_dir / "raw" / "geocode.json").write_text(json.dumps(geo.raw, ensure_ascii=False, indent=2), encoding="utf-8")
        (out_dir / "raw" / "routes.json").write_text(json.dumps(ro.raw, ensure_ascii=False, indent=2), encoding="utf-8")

    origin, dest = geo.places[0], geo.places[-1]
    out = extract_turns(ro.route, origin, dest)
    e = out.exploration
    (out_dir / "route.json").write_text(e.model_dump_json(indent=2), encoding="utf-8")
    title = f"曲がり角: {origin.query} → {dest.query}（{e.total_distance_m} m, 採用 {len(e.points)} / 候補 {len(out.decisions)}）"
    (out_dir / "map.html").write_text(build_map(title, out), encoding="utf-8")

    print(title)
    for d in out.decisions:
        c = d.candidate
        mark = f"採用 {d.turn:<8}" if d.accepted else f"不採用({d.reason})"
        delta = "-" if c.delta_deg is None else f"{c.delta_deg:+.0f}°"
        print(f"  {mark:<28} {c.maneuver or '-':<18} Δ{delta:>6}  {c.instruction}")
    print(f"\n地図: {out_dir / 'map.html'}")


if __name__ == "__main__":
    main()

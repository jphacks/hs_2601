"""写真順の地図（手順 6）。経路計算の前に「出発地 → 写真 1 → … → 目的地」の順を目視する。"""
from __future__ import annotations

import html

from app.schemas.creator_input import PlanInput
from app.schemas.exploration import Place
from app.services.creator.mapview import MapSpec, Marker, render_map_html


def render_photos_map(plan: PlanInput, origin: Place, destination: Place) -> str:
    markers = [Marker(origin.lat, origin.lng, "S", f"<b>出発</b> {html.escape(origin.query)}", "green")]
    for p in plan.photos:
        acc = f" / 精度 {p.accuracy_m:.0f} m" if p.accuracy_m is not None else ""
        cap = f"<br>{html.escape(p.caption)}" if p.caption else ""
        popup = f"<b>写真 {p.seq}</b> ({p.lat:.5f}, {p.lng:.5f}){acc}{cap}<br><img src=\"{html.escape(p.image)}\" width=\"280\">"
        markers.append(Marker(p.lat, p.lng, str(p.seq), popup, "#2e7d32"))
    if plan.ends_at_last_photo:  # 最後の写真がゴール。G は付けず、その写真の印を赤にする
        markers[-1] = Marker(markers[-1].lat, markers[-1].lng, markers[-1].label, f"<b>ゴール</b> {markers[-1].popup_html}", "red")
    else:
        markers.append(Marker(destination.lat, destination.lng, "G", f"<b>目的地</b> {html.escape(destination.query)}", "red"))
    path = [(m.lat, m.lng) for m in markers]
    title = f"写真順: {origin.query} → {destination.query}（写真 {len(plan.photos)} 枚）"
    return render_map_html(MapSpec(title=title, markers=markers, path=path, data=plan.model_dump(mode="json")))

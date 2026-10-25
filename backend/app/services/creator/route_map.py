"""経路の確認用地図（map.html）。経路線と地点ピン（番号・曲がる向きの色）、クリックで採用画像。

CLI（scripts/*）と作る人 API（pipeline.write_route_files）の両方が中間ファイルとして書く。
"""
from __future__ import annotations

import html

from app.schemas.exploration import Exploration
from app.services.creator.contact import TURN_LABEL
from app.services.creator.mapview import MapSpec, Marker, render_map_html
from app.services.creator.route import decode_polyline

TURN_COLOR = {"left": "orange", "right": "purple", "straight": "blue", "arrive": "red"}
DEPART_COLOR = "green"


def _popup(p) -> str:
    shown = p.arrow_image or p.image
    img = f'<br><img src="{html.escape(shown)}" width="280">' if shown else "<br>(Street View なし)"
    return f"<b>{p.index} {TURN_LABEL[p.turn]}</b> 次まで {p.distance_to_next_m} m<br>{html.escape(p.instruction)}{img}"


def render_route_map(e: Exploration, title: str) -> str:
    markers = [
        Marker(p.lat, p.lng, str(p.index), _popup(p),
               DEPART_COLOR if p.maneuver.upper() == "DEPART" else TURN_COLOR.get(p.turn, "blue"))
        for p in e.points
    ]
    path = decode_polyline(e.polyline) if e.polyline else []
    return render_map_html(MapSpec(title=title, markers=markers, path=path))

"""確認用の地図 HTML を生成する（Leaflet + 地理院タイル、API キー不要）。

ピンと経路線を描き、下部に JSON をそのまま表示する。開発者が目視確認するためのもので、
フロントエンドには使わない。
"""
from __future__ import annotations

import html
import json
from dataclasses import dataclass, field
from typing import Any

LEAFLET_CSS = "https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"
LEAFLET_JS = "https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"


@dataclass(frozen=True)
class Marker:
    lat: float
    lng: float
    label: str
    popup_html: str = ""
    color: str = "blue"  # blue / red / green など CSS 色名


@dataclass(frozen=True)
class MapSpec:
    title: str
    markers: list[Marker] = field(default_factory=list)
    path: list[tuple[float, float]] = field(default_factory=list)  # [(lat, lng), ...]
    data: Any = None  # 下部に表示する JSON


def render_map_html(spec: MapSpec) -> str:
    markers_js = json.dumps(
        [
            {"lat": m.lat, "lng": m.lng, "label": m.label, "popup": m.popup_html, "color": m.color}
            for m in spec.markers
        ],
        ensure_ascii=False,
    )
    path_js = json.dumps([[lat, lng] for lat, lng in spec.path])
    data_text = html.escape(json.dumps(spec.data, ensure_ascii=False, indent=2)) if spec.data is not None else ""
    return f"""<!doctype html>
<html lang="ja">
<head>
<meta charset="utf-8">
<title>{html.escape(spec.title)}</title>
<link rel="stylesheet" href="{LEAFLET_CSS}">
<style>
  body {{ margin: 0; font-family: system-ui, sans-serif; }}
  #map {{ height: 70vh; }}
  h1 {{ font-size: 1rem; margin: .5rem 1rem; }}
  pre {{ margin: 0 1rem 1rem; padding: 1rem; background: #f4f4f4; overflow: auto; max-height: 28vh; font-size: .8rem; }}
  .pin {{ width: 26px; height: 26px; border-radius: 50% 50% 50% 0; transform: rotate(-45deg);
          border: 2px solid #fff; box-shadow: 0 0 2px #0006; display: flex; align-items: center; justify-content: center; }}
  .pin span {{ transform: rotate(45deg); color: #fff; font-size: 12px; font-weight: bold; }}
</style>
</head>
<body>
<h1>{html.escape(spec.title)}</h1>
<div id="map"></div>
<pre>{data_text}</pre>
<script src="{LEAFLET_JS}"></script>
<script>
  const markers = {markers_js};
  const path = {path_js};
  const map = L.map('map', {{ fadeAnimation: false, zoomAnimation: false }});
  // 地理院タイル（国土地理院）。無料・キー不要で日本の地図が日本語表記で出る。
  // OpenStreetMap 本家は file:// から開くと利用ポリシーでブロックされるため使わない。
  L.tileLayer('https://cyberjapandata.gsi.go.jp/xyz/pale/{{z}}/{{x}}/{{y}}.png', {{
    maxZoom: 18,
    attribution: '<a href="https://maps.gsi.go.jp/development/ichiran.html">地理院タイル</a>'
  }}).addTo(map);
  const bounds = [];
  if (path.length > 1) {{
    L.polyline(path, {{ color: '#1a73e8', weight: 5 }}).addTo(map);
    path.forEach(p => bounds.push(p));
  }}
  markers.forEach(m => {{
    const icon = L.divIcon({{
      className: '', iconSize: [26, 26], iconAnchor: [13, 26], popupAnchor: [0, -24],
      html: `<div class="pin" style="background:${{m.color}}"><span>${{m.label}}</span></div>`
    }});
    const mk = L.marker([m.lat, m.lng], {{ icon }}).addTo(map);
    if (m.popup) mk.bindPopup(m.popup);
    bounds.push([m.lat, m.lng]);
  }});
  if (bounds.length) map.fitBounds(bounds, {{ padding: [40, 40] }});
  else map.setView([34.70, 135.50], 13);
</script>
</body>
</html>
"""

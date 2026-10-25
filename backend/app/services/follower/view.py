"""参加者側の確認用表示。写真列を画像付きの HTML にする（フロントの代わり）。"""
from __future__ import annotations

import html

from app.schemas.route_plan import RoutePlanRecord
from app.services.creator.contact import TURN_LABEL

STYLE = (
    "body{font-family:sans-serif;margin:16px}"
    ".g{display:grid;grid-template-columns:repeat(auto-fill,minmax(320px,1fr));gap:16px}"
    "figure{margin:0}img{width:100%}.none{aspect-ratio:1;background:#eee;display:grid;place-items:center}"
)


def _card(s) -> str:
    img = f'<img src="{html.escape(s.image_url)}" alt="">' if s.image_url else '<div class="none">画像なし</div>'
    return (
        f"<figure>{img}<figcaption><b>{s.index} {html.escape(TURN_LABEL[s.turn])}</b> 次まで {s.distance_to_next_m} m<br>"
        f"{html.escape(s.landmark or '')}<br><small>{html.escape(s.instruction)}</small></figcaption></figure>"
    )


def render_plan_html(rec: RoutePlanRecord) -> str:
    cards = "".join(_card(s) for s in rec.plan.steps)
    return (
        f"<!doctype html><meta charset=utf-8><title>{html.escape(rec.name)}</title><style>{STYLE}</style>"
        f"<h1>{html.escape(rec.name)} <small>id={html.escape(rec.id)}</small></h1>"
        f"<p>{html.escape(rec.origin)} → {html.escape(rec.destination)}（{rec.plan.total_distance_m} m, {len(rec.plan.steps)} 地点）</p>"
        f'<div class="g">{cards}</div>'
    )

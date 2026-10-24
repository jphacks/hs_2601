"""確認用の画像一覧ページ。route.json の点を経路順にカードで並べる。"""
from __future__ import annotations

import html

from app.schemas.exploration import Exploration

TURN_LABEL = {"left": "← 左", "right": "→ 右", "straight": "↑ 直進", "arrive": "● 到着"}
TURN_COLOR = {"left": "#f29100", "right": "#7b1fa2", "straight": "#1a73e8", "arrive": "#d32f2f"}


def render_contact_html(e: Exploration, title: str) -> str:
    cards = []
    for p in e.points:
        shown = p.arrow_image or p.image
        img = (
            f'<img src="{html.escape(shown)}" alt="">'
            if shown
            else '<div class="noimg">Street View なし</div>'
        )
        sv = p.street_view
        src = ("公式" if "google" in (sv.copyright or "").lower() else "投稿") if sv else ""
        meta = f"撮影 {sv.date or '不明'} / {src} / 手前 {sv.offset_m:.0f} m / heading {sv.heading:.0f}° / fov {sv.fov}°" if sv else ""
        cand_html = ""
        if p.candidates:
            items = []
            for i, c in enumerate(p.candidates):
                chosen = " chosen" if p.chosen_candidate == i else ""
                sc = c.score
                if sc and (not sc.on_walkway or sc.path_blocked):
                    chosen += " rejected"
                    why = "立てない" if not sc.on_walkway else "進めない"
                    label = f"{why} / 現在地 {sc.here} / 矢印 {sc.arrow}"
                else:
                    label = f"現在地 {sc.here} / 矢印 {sc.arrow}" if sc else "未評価"
                items.append(
                    f'<figure class="cand{chosen}"><img src="{html.escape(c.image)}" alt="">'
                    f'<figcaption>#{i} {html.escape(c.heading_mode)} {("先" if c.street_view.offset_m < 0 else "手前")}{abs(c.street_view.offset_m):.0f}m fov{c.street_view.fov}<br>{label}</figcaption></figure>'
                )
            cand_html = f'<div class="cands">{"".join(items)}</div>'
        cards.append(
            f"""<article>
  <header><span class="idx">{p.index}</span>
    <span class="turn" style="background:{TURN_COLOR[p.turn]}">{TURN_LABEL[p.turn]}</span>
    <span class="dist">次まで {p.distance_to_next_m} m</span></header>
  {img}
  <p class="ins">{html.escape(p.instruction or '(案内文なし)')}</p>
  <p class="meta">{html.escape(p.maneuver)} / {html.escape(meta)}</p>
  <p class="lm">{html.escape(p.landmark or '目印: (ステップ 7 で生成)')}</p>
  {cand_html}
</article>"""
        )
    return f"""<!doctype html>
<html lang="ja"><head><meta charset="utf-8"><title>{html.escape(title)}</title>
<style>
  body {{ margin: 0; padding: 1rem; font-family: system-ui, sans-serif; background: #fafafa; }}
  h1 {{ font-size: 1.1rem; }}
  main {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(320px, 1fr)); gap: 1rem; }}
  article {{ background: #fff; border-radius: 8px; box-shadow: 0 1px 3px #0002; overflow: hidden; }}
  header {{ display: flex; gap: .5rem; align-items: center; padding: .5rem .75rem; }}
  .idx {{ font-weight: bold; font-size: 1.2rem; }}
  .turn {{ color: #fff; padding: .1rem .5rem; border-radius: 4px; font-size: .9rem; }}
  .dist {{ margin-left: auto; color: #555; font-size: .9rem; }}
  img {{ width: 100%; aspect-ratio: 1; object-fit: cover; display: block; }}
  .noimg {{ aspect-ratio: 1; display: flex; align-items: center; justify-content: center; background: #eee; color: #888; }}
  p {{ margin: .4rem .75rem; font-size: .9rem; }}
  .meta {{ color: #888; font-size: .75rem; }}
  .lm {{ color: #1a73e8; }}
  .cands {{ display: flex; flex-wrap: wrap; gap: .4rem; padding: .5rem .75rem .75rem; }}
  .cand {{ margin: 0; flex: 0 0 96px; border: 3px solid transparent; border-radius: 6px; }}
  .cand.chosen {{ border-color: #1a73e8; }}
  .cand.rejected img {{ opacity: .35; }}
  .cand.rejected figcaption {{ color: #c00; }}
  .cand img {{ width: 96px; height: 96px; object-fit: cover; border-radius: 3px; }}
  .cand figcaption {{ font-size: .65rem; color: #666; line-height: 1.2; }}
</style></head>
<body><h1>{html.escape(title)}</h1><main>{''.join(cards)}</main></body></html>
"""

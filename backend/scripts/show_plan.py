"""確認用: Supabase に保存した写真列を、参加者と同じ anon キーで取り出して表示する。

使い方:
  python -m scripts.show_plan --qr ./out/cases/5/qr.png         # QR を読んで URL → id → 取得（参加者の流れ）
  python -m scripts.show_plan --name "四天王寺→てんしば"
  python -m scripts.show_plan --id 7298a7dd6554
  python -m scripts.show_plan --list                  # 保存済みの一覧
  python -m scripts.show_plan --name "..." --html ./out/plan.html   # 画像を並べた HTML を書き出す

前提: .env の SUPABASE_URL と SUPABASE_ANON_KEY（service_role は使わない。参加者が見える範囲だけを確認するため）。
"""
from __future__ import annotations

import argparse
from pathlib import Path

from app.core.config import get_settings
from app.external.supabase.rest import SupabaseRest
from app.imaging.qr import read_qr
from app.repositories.supabase_repo import TABLE, SupabaseRoutePlanRepository
from app.services.creator.contact import TURN_LABEL
from app.services.follower.fetch import fetch_plan, plan_id_from_url
from app.services.follower.view import render_plan_html


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--name")
    g.add_argument("--id")
    g.add_argument("--qr", type=Path, help="QR 画像（PNG）を読んで、その URL の id を取得する")
    g.add_argument("--list", action="store_true")
    ap.add_argument("--html", type=Path, default=None, help="画像一覧 HTML の出力先")
    args = ap.parse_args()

    settings = get_settings()
    if not settings.supabase_url or not settings.supabase_anon_key:
        raise SystemExit("SUPABASE_URL と SUPABASE_ANON_KEY を .env に書いてください。")
    rest = SupabaseRest(settings.supabase_url, settings.supabase_anon_key)

    if args.list:
        rows = rest.select(TABLE, {"order": "updated_at.desc"}, columns="id,name,origin,destination,updated_at")
        for r in rows:
            print(f"{r['id']}  {r['name']:<24} {r['origin']} → {r['destination']}  {r['updated_at'][:16]}")
        print(f"\n{len(rows)} 件")
        return

    repo = SupabaseRoutePlanRepository(rest)
    if args.qr:
        url = read_qr(args.qr.read_bytes())
        if not url:
            raise SystemExit(f"QR を読めませんでした: {args.qr}")
        plan_id = plan_id_from_url(url)
        print(f"QR: {url}  →  id={plan_id}")
        rec = fetch_plan(repo, plan_id)
    else:
        rec = repo.get_by_name(args.name) if args.name else fetch_plan(repo, args.id)
    if rec is None:
        raise SystemExit("見つかりません（未保存か、status が published ではない）。")
    print(f"{rec.name}  id={rec.id}  {rec.origin} → {rec.destination}  {len(rec.plan.steps)} 地点")
    for s in rec.plan.steps:
        print(f"  {s.index:2d} {TURN_LABEL[s.turn]:<6} {s.landmark or '':<20} {s.image_url or '(画像なし)'}")
    if args.html:
        args.html.write_text(render_plan_html(rec), encoding="utf-8")
        print(f"\nHTML: {args.html}")


if __name__ == "__main__":
    main()

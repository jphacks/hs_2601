"""ステップ 6: 出発地と目的地から、交差点の写真列（route.json + 画像）を一括生成する。

使い方:
  python -m scripts.explore_route "大阪駅" "グランフロント大阪" --out ./out
  python -m scripts.explore_route "大阪駅" "グランフロント大阪" --via "梅田スカイビル" --out ./out
  python -m scripts.explore_route "大阪駅" "グランフロント大阪" --no-cache     # キャッシュを使わず必ず API を叩く
  python -m scripts.explore_route "大阪駅" "グランフロント大阪" --name "大阪駅→グランフロント"   # 最後に Supabase へ保存
  python -m scripts.explore_route --photos ./out/cases/6 --out ./out/cases/6 --publish          # 作成者写真を通る経路（photos.json から）

処理: geocode → route → turns → streetview（候補を複数）→ landmark（VLM が採点して 1 枚を選び、目印文と矢印の経路を返す）→ arrow（曲線の矢印を描く）
      --photos のときは route → turns を「区間ごとに計算して結合」に置き換え、写真地点は写真をそのまま使う（Street View・VLM・矢印なし）
      → --name があれば publish（命名をキーに Supabase の route_plans と plans バケットへ保存。同名は上書き）
出力: out/route.json, out/images/, out/raw/, out/map.html, out/contact.html, map.png, contact.png（PNG は --no-png で省略）
      --name 時は out/published.json と、PUBLIC_BASE_URL があれば out/qr.png も
キャッシュ: 同じ地名・座標・パノラマ・画像+プロンプトなら backend/.cache/ を再利用する。
VLM のキーが無いときは --no-vlm と同じ（フォールバック文のみ）。
"""
from __future__ import annotations

import argparse
from pathlib import Path

from app.core.config import get_settings
from app.external.supabase.rest import SupabaseRest
from app.repositories.supabase_repo import SupabasePhotoStorage, SupabaseRoutePlanRepository
from app.services.creator.contact import TURN_LABEL
from app.services.creator.photos import load_plan_input
from app.services.creator.pipeline import (
    PipelineResult, Reporter, enrich, explore_photos, explore_queries, make_clients, route_title, write_route_files,
)
from app.services.creator.publish import publish_plan
from app.services.creator.qr import write_qr
from app.services.creator.streetview import StreetViewOptions
from scripts.snapshot_map import write_snapshots
from scripts.streetview import build_map


def parse_args() -> tuple[argparse.ArgumentParser, argparse.Namespace]:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("origin", nargs="?", default=None)
    ap.add_argument("destination", nargs="?", default=None)
    ap.add_argument("--photos", type=Path, default=None, help="photos.json があるディレクトリ（作成者写真を通る経路）。出発地・目的地はそこから読む")
    ap.add_argument("--publish", action="store_true", help="--photos の命名で Supabase へ保存する（--name があればそちらを優先）")
    ap.add_argument("--via", action="append", default=[], help="経由地（複数可）")
    ap.add_argument("--out", type=Path, default=None, help="出力先（既定: backend/out）")
    ap.add_argument("--no-cache", action="store_true", help="キャッシュを使わない")
    ap.add_argument("--heading", choices=["approach", "bisector", "departure"], default="bisector")
    ap.add_argument("--fov", type=int, default=90)
    ap.add_argument("--pitch", type=int, default=0)
    ap.add_argument("--offset-m", type=float, default=0.0)
    ap.add_argument("--no-vlm", action="store_true", help="VLM の採点を行わず、フォールバック文だけ付ける")
    ap.add_argument("--no-png", action="store_true", help="map.png と contact.png を出さない（既定は Firefox があれば出す）")
    ap.add_argument("--name", default=None, help="命名をキーにして Supabase へ保存する（同名は上書き）")
    ap.add_argument("--id", default=None, help="--name と併用。公開 ID を指定する（既定: 命名のハッシュ）")
    return ap, ap.parse_args()


def write_outputs(r: PipelineResult, out_dir: Path, no_png: bool) -> None:
    write_route_files(r, out_dir)
    (out_dir / "map.html").write_text(build_map(r.exploration, route_title(r)), encoding="utf-8")
    for p in r.exploration.points:
        print(f"  {p.index:2d} {TURN_LABEL[p.turn]:<6} 次まで {p.distance_to_next_m:4d} m  候補 {len(p.candidates)}  {p.landmark or ''}")
    print(f"\n一覧: {out_dir / 'contact.html'}\n地図: {out_dir / 'map.html'}")
    if not no_png:
        write_snapshots(out_dir)


def save_to_supabase(r: PipelineResult, out_dir: Path, name: str, supabase: SupabaseRest, plan_id: str | None) -> None:
    """9. 命名をキーに Supabase へ保存し、PUBLIC_BASE_URL があれば QR も出す。"""
    settings = get_settings()
    res = publish_plan(r.exploration, out_dir, name, SupabaseRoutePlanRepository(supabase), SupabasePhotoStorage(supabase), plan_id=plan_id)
    (out_dir / "published.json").write_text(res.record.model_dump_json(indent=2), encoding="utf-8")
    print(f"[9] publish: name={res.record.name!r} id={res.record.id}  画像 {len(res.uploaded)} / なし {len(res.skipped)}")
    print(f"    取得: {settings.supabase_url}/rest/v1/route_plans?name=eq.{res.record.name}  （apikey: anon キー）")
    if settings.public_base_url:
        qr = write_qr(out_dir, settings.public_base_url, res.record.id)
        print(f"    QR: {qr.path}  →  {qr.url}")


def main() -> None:
    ap, args = parse_args()
    plan = load_plan_input(args.photos) if args.photos else None
    if plan is None and not (args.origin and args.destination):
        ap.error("出発地と目的地、または --photos を指定してください")
    publish_name = args.name or (plan.name if plan and args.publish else None)

    settings = get_settings()
    clients = make_clients(settings, use_cache=not args.no_cache, use_vlm=not args.no_vlm)
    supabase = SupabaseRest(*settings.require_supabase()) if publish_name else None  # 保存先の設定不足は最初に気づく
    out_dir: Path = args.out or settings.out_dir
    (out_dir / "raw").mkdir(parents=True, exist_ok=True)
    rep = Reporter(log=print)

    if plan is None:
        r = explore_queries(clients, [args.origin, *args.via, args.destination], out_dir, rep)
    else:
        r = explore_photos(clients, plan, out_dir, rep, src_dir=args.photos)

    opt = StreetViewOptions(offset_m=args.offset_m, fov=args.fov, pitch=args.pitch, heading_mode=args.heading)
    r = PipelineResult(enrich(clients, r.exploration, out_dir, opt, rep), r.origin, r.destination)
    write_outputs(r, out_dir, args.no_png)
    if supabase:
        save_to_supabase(r, out_dir, publish_name, supabase, args.id)


if __name__ == "__main__":
    main()

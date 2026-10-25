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
import json
from pathlib import Path

from app.core.config import get_settings
from app.external.google.geocoding import GeocodingClient
from app.external.google.routes import RoutesClient
from app.external.google.street_view import StreetViewClient
from app.external.vlm.base import VlmError
from app.external.vlm.factory import make_vlm_client
from app.external.supabase.rest import SupabaseRest
from app.repositories.supabase_repo import SupabasePhotoStorage, SupabaseRoutePlanRepository
from app.services.creator.cache import FileCache
from app.services.creator.contact import TURN_LABEL, render_contact_html
from app.services.creator.geocode import geocode_queries
from app.services.creator.route import compute_route
from app.services.creator.arrow import draw_arrows
from app.services.creator.landmark import evaluate_landmarks
from app.services.creator.legs import merge_legs, plan_legs, split_legs
from app.services.creator.photos import load_plan_input, normalize_photo
from app.services.creator.publish import publish_plan
from app.services.creator.qr import write_qr
from app.services.creator.streetview import StreetViewOptions, fetch_candidates
from app.services.creator.turns import extract_turns
from scripts.photos_map import resolve_places
from scripts.snapshot_map import write_snapshots
from scripts.streetview import build_map


def main() -> None:
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
    args = ap.parse_args()
    plan = load_plan_input(args.photos) if args.photos else None
    if plan is None and not (args.origin and args.destination):
        ap.error("出発地と目的地、または --photos を指定してください")
    publish_name = args.name or (plan.name if plan and args.publish else None)

    settings = get_settings()
    key = settings.require_google_maps_api_key()
    supabase = SupabaseRest(*settings.require_supabase()) if publish_name else None  # 保存先の設定不足は最初に気づく
    out_dir: Path = args.out or settings.out_dir
    (out_dir / "raw").mkdir(parents=True, exist_ok=True)
    cache = None if args.no_cache else FileCache(settings.cache_dir, "google")

    if plan is None:
        # 2. geocode
        geo = geocode_queries(GeocodingClient(key), [args.origin, *args.via, args.destination], cache)
        origin, dest, via = geo.places[0], geo.places[-1], geo.places[1:-1]
        (out_dir / "raw" / "geocode.json").write_text(json.dumps(geo.raw, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"[2/7] geocode: {origin.query} ({origin.lat:.5f},{origin.lng:.5f}) → {dest.query} ({dest.lat:.5f},{dest.lng:.5f})")

        # 3. route
        ro = compute_route(RoutesClient(key), origin, dest, via, cache)
        (out_dir / "raw" / "routes.json").write_text(json.dumps(ro.raw, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"[3/7] route: {ro.route.distance_m} m, 約 {ro.route.duration_s // 60} 分, {len(ro.route.steps)} ステップ")

        # 4. turns
        turns = extract_turns(ro.route, origin, dest)
        e = turns.exploration
        print(f"[4/7] turns: 採用 {len(e.points)} / 候補 {len(turns.decisions)}")
    else:
        # 2. geocode（座標が無いときだけ）
        origin, dest = resolve_places([plan.origin, plan.destination], cache)
        print(f"[2/7] geocode: {origin.query} ({origin.lat:.5f},{origin.lng:.5f}) → {dest.query} ({dest.lat:.5f},{dest.lng:.5f})  写真 {len(plan.photos)} 枚")

        # 写真を出力ディレクトリへ（正規化して photos/ に置く）
        if args.photos.resolve() != out_dir.resolve():
            (out_dir / "photos").mkdir(parents=True, exist_ok=True)
            for ph in plan.photos:
                (out_dir / ph.image).write_bytes(normalize_photo((args.photos / ph.image).read_bytes()))
            (out_dir / "photos.json").write_text(plan.model_dump_json(indent=2), encoding="utf-8")

        # 3. 区間ごとの経路
        legs = split_legs(origin, dest, plan.photos)
        outputs, leg_warnings = plan_legs(RoutesClient(key), legs, cache)
        (out_dir / "legs").mkdir(exist_ok=True)
        for leg, out in zip(legs, outputs):
            if out:
                (out_dir / "legs" / f"{leg.index:02d}.json").write_text(json.dumps(out.raw, ensure_ascii=False, indent=2), encoding="utf-8")
        ok = [o for o in outputs if o]
        print(f"[3/7] route: 区間 {len(ok)}/{len(legs)}, 計 {sum(o.route.distance_m for o in ok)} m")

        # 4. 区間ごとの曲がり角 → 結合
        merged = merge_legs(legs, outputs, origin, dest)
        e = merged.exploration
        n_photo = sum(1 for p in e.points if p.image_source == "creator_photo")
        print(f"[4/7] turns: 採用 {len(e.points)}（うち作成者写真 {n_photo}）")
        for w in [*leg_warnings, *merged.warnings]:
            print(f"      ! {w.message}")

    # 5. street view（候補を複数）
    opt = StreetViewOptions(offset_m=args.offset_m, fov=args.fov, pitch=args.pitch, heading_mode=args.heading)
    e, stats = fetch_candidates(StreetViewClient(key), e, out_dir, opt, cache=cache)
    n_cand = sum(len(p.candidates) for p in e.points)
    print(f"[5/7] street view: 地点 {len(stats.fetched)} / なし {len(stats.missing)}, 候補 {n_cand} 枚")

    # 7. VLM が採点して 1 枚を選び、目印文を付ける
    vlm = None
    if not args.no_vlm:
        try:
            vlm = make_vlm_client(settings)
        except VlmError as err:
            print(f"[6/7] VLM なし（{err}）→ フォールバック文のみ")
    e, lstats = evaluate_landmarks(vlm, e, out_dir, None if args.no_cache else FileCache(settings.cache_dir, "vlm"))
    if vlm:
        print(f"[6/7] landmark ({vlm.model}): 評価 {len(lstats.evaluated)} / フォールバック {len(lstats.fallback)}")
        for i, msg in lstats.errors.items():
            print(f"      ! 地点 {i}: {msg}")

    # 8. 矢印
    e, astats = draw_arrows(e, out_dir)
    print(f"[7/7] arrow: 描画 {len(astats.drawn)}（投影 {len(astats.with_geo_path)} / VLM {len(astats.with_vlm_path)}）/ 画像なし {len(astats.skipped)} / 作成者写真 {len(astats.creator)}")

    title = f"{origin.query} → {dest.query}（{e.total_distance_m} m, {len(e.points)} 地点）"
    (out_dir / "route.json").write_text(e.model_dump_json(indent=2), encoding="utf-8")
    (out_dir / "contact.html").write_text(render_contact_html(e, title), encoding="utf-8")
    (out_dir / "map.html").write_text(build_map(e, title), encoding="utf-8")

    for p in e.points:
        print(f"  {p.index:2d} {TURN_LABEL[p.turn]:<6} 次まで {p.distance_to_next_m:4d} m  候補 {len(p.candidates)}  {p.landmark or ''}")
    print(f"\n一覧: {out_dir / 'contact.html'}\n地図: {out_dir / 'map.html'}")
    if not args.no_png:
        write_snapshots(out_dir)

    # 9. 命名をキーに Supabase へ保存
    if supabase:
        res = publish_plan(e, out_dir, publish_name, SupabaseRoutePlanRepository(supabase), SupabasePhotoStorage(supabase), plan_id=args.id)
        (out_dir / "published.json").write_text(res.record.model_dump_json(indent=2), encoding="utf-8")
        print(f"[9] publish: name={res.record.name!r} id={res.record.id}  画像 {len(res.uploaded)} / なし {len(res.skipped)}")
        print(f"    取得: {settings.supabase_url}/rest/v1/route_plans?name=eq.{res.record.name}  （apikey: anon キー）")
        if settings.public_base_url:
            qr = write_qr(out_dir, settings.public_base_url, res.record.id)
            print(f"    QR: {qr.path}  →  {qr.url}")


if __name__ == "__main__":
    main()

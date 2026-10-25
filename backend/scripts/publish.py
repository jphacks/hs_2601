"""ステップ 9: 出力ディレクトリの写真列を、命名をキーにして Supabase に保存する。

使い方:
  python -m scripts.publish --from-route ./out/cases/5 --name "四天王寺→てんしば"
  python -m scripts.publish --from-route ./out/cases/5 --name "四天王寺→てんしば" --id abc123   # ID を自分で決める

前提: .env に SUPABASE_URL と SUPABASE_SERVICE_ROLE_KEY。テーブルとバケットは `supabase db push` で作る。
出力: Supabase の route_plans に 1 行、plans バケットに画像。<dir>/published.json に保存内容の控え。
      .env に PUBLIC_BASE_URL があれば <dir>/qr.png（{PUBLIC_BASE_URL}/r/<id> の QR）。
同じ --name で実行し直すと同じ ID に上書きされる。
"""
from __future__ import annotations

import argparse
from pathlib import Path

from app.core.config import get_settings
from app.external.supabase.rest import SupabaseRest
from app.repositories.supabase_repo import SupabasePhotoStorage, SupabaseRoutePlanRepository
from app.schemas.exploration import Exploration
from app.services.creator.contact import TURN_LABEL
from app.services.creator.publish import publish_plan
from app.services.creator.qr import write_qr


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--from-route", type=Path, required=True, help="route.json があるディレクトリ")
    ap.add_argument("--name", required=True, help="写真列の命名（検索キー。同名は上書き）")
    ap.add_argument("--id", default=None, help="公開 ID を指定する（既定: 命名のハッシュ）")
    args = ap.parse_args()

    settings = get_settings()
    url, key = settings.require_supabase()
    rest = SupabaseRest(url, key)
    d: Path = args.from_route
    e = Exploration.model_validate_json((d / "route.json").read_text(encoding="utf-8"))

    result = publish_plan(e, d, args.name, SupabaseRoutePlanRepository(rest), SupabasePhotoStorage(rest), plan_id=args.id)
    rec = result.record
    (d / "published.json").write_text(rec.model_dump_json(indent=2), encoding="utf-8")

    print(f"保存: {rec.name}  id={rec.id}  ({rec.origin} → {rec.destination}, {len(rec.plan.steps)} 地点, 画像 {len(result.uploaded)} / なし {len(result.skipped)})")
    for s in rec.plan.steps:
        print(f"  {s.index:2d} {TURN_LABEL[s.turn]:<6} {s.image_url or '(画像なし)'}")
    print(f"\n取得: {url}/rest/v1/route_plans?id=eq.{rec.id}  （apikey ヘッダーに anon キー）")
    print(f"控え: {d / 'published.json'}")
    if settings.public_base_url:
        qr = write_qr(d, settings.public_base_url, rec.id)
        print(f"QR: {qr.path}  →  {qr.url}")
    else:
        print("QR: PUBLIC_BASE_URL が未設定なので省略（.env に参加者画面の URL を書くと qr.png を出す）")


if __name__ == "__main__":
    main()

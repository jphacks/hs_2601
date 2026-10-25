# shared/fixtures

バックエンドなしで画面を開発・確認するためのサンプルデータ。

- `sampleRoutePlan.json`: 写真列 JSON（RoutePlan）。`backend/out/cases/5/published.json` の `plan` をそのまま置いたもの。
  画像 URL は Supabase の公開バケットを指すので、そのまま表示できる。

更新するときは backend の `scripts.publish` を実行して出た `published.json` の `plan` をコピーする。

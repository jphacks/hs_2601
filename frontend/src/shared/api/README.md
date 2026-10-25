# shared/api（通信層）

バックエンドとの通信だけを担当する。画面や状態のことは知らない。

- `endpoints.ts`: 入口。`routeApi` を export する。creator / follower はこれだけを import する
- `types.ts`: 5 本の API（+ 参加者向け詳細取得）を関数にした `RouteApi` インターフェース
- `fixtureApi.ts`: バックエンドなしで動く実装。`shared/fixtures/` のサンプルを返す（既定）
- `serverApi.ts`: FastAPI を呼ぶ実装。`VITE_API_MODE=server` で有効。契約は docs/interface.md 5 章
- `planManifest.ts`: 作成受付で送る manifest（4 章 PlanInput）を組み立てる純粋関数
- `errors.ts`: API の失敗（`{detail}`・状態コード）を利用者向けの日本語にする
- `client.ts`: fetch ラッパー。base URL の解決（`apiUrl`、QR 画像にも使う）、JSON 変換、エラーの例外化

依存: `shared/types/`、`shared/fixtures/`、`shared/lib/` のみ。`creator/`、`follower/` は import しない。

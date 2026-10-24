# shared/api（通信層）

バックエンドとの通信だけを担当する。画面や状態のことは知らない。

- `client.ts`: fetch ラッパー。base URL の解決、JSON 変換、エラーの例外化
- 今後: `endpoints.ts` に 5 本の API を型付き関数として追加する

依存: `shared/types/` のみ。`creator/`、`follower/` は import しない。

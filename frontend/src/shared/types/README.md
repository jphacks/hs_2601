# shared/types

フロント・バック間でやり取りするデータの型。

- `routePlan.ts`: 写真列 JSON（RoutePlan、RouteStep）。`backend/app/schemas/route_plan.py` と 1:1
- `creator.ts`: 作成受付・ジョブ状態・一覧・公開結果。`backend/app/schemas/creator.py`（未作成）と 1:1 にする

- 変更するときはバックエンドの schemas も同時に変更する。

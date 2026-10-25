# creator/hooks（操作層）

作る人のボタン・操作に対する処理。状態管理、Geolocation、ジョブのポーリングなど。

- `useCreatorDraft.ts`: 作成中の入力（出発地・目的地・写真）。CreatorRoot で 1 回呼び、配下は `useDraft()` で受け取る
- `useCapture.ts`: File 取得と同時に Geolocation で座標を取る。Object URL の後始末も担う
- `useCreateRoute.ts`: 入力の検証と作成受付 API 呼び出し。エラーは state で返す（alert は使わない）
- `useJobPolling.ts`: ステータス API を数秒おきに叩く
- `useRoutePlan.ts`: 作成結果の写真列を取得する
- `useRouteList.ts`: 一覧取得、チェック選択、公開

- 通信は `shared/api/endpoints.ts` を呼ぶ。fetch は直書きしない。
- 見た目は持たない。戻り値（状態とハンドラ）を `pages/` が components に渡す。

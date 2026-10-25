# shared/components

作る人・参加者の両方で使う見た目の部品。

- `StepView.tsx`: 1 ステップ（写真 + 矢印 + 目印文 + 次までの距離）
- `RoutePlanViewer.tsx`: 写真列全体。進捗バーと「前へ」「次へ」を持つ

- props だけで動く。通信・位置情報は持たない。
- 例外として、表示位置（現在ステップ）のような UI 内部の状態だけは持ってよい。
  外から制御したいときは `current` / `onCurrentChange` を渡す。

# shared

作る人（creator）と参加者（follower）の両方が使うもの。

- `types/`: 写真列 JSON などフロント・バック間の型
- `api/`: 5 本の API の入口（`endpoints.ts`）。fixture 実装と server 実装を切り替える
- `fixtures/`: バックエンドなしで動かすためのサンプルデータ
- `components/`: 写真列の共用表示（`RoutePlanViewer`、`StepView`）
- `hooks/`: 画面に依存しない小さな hooks（`useAsync`）
- `lib/`: 定数・純関数

- `creator/` と `follower/` からのみ import される。逆方向の import はしない（oxlint の `no-restricted-imports` で検査）。
- ここを変更するときは両担当に声をかける。

# follower/logic

React や DOM に依存しない純関数。単体テストの主対象。

- `qrPayload.ts`: QR の中身（URL か ID）から道案内 ID を取り出す
- 今後: `arrival.ts`（到達判定）、`overshoot.ts`（通り過ぎ判定）、`offRoute.ts`（経路外れ判定）

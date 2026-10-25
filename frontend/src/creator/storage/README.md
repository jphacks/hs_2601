# creator/storage（永続化）

ブラウザ内に残すデータ。

- `creatorId.ts`: localStorage の作成者 ID
- 今後: `photoStore.ts`（IndexedDB に写真と座標を保存。現状はメモリ保持でリロードすると消える）

- React に依存しない。hooks から呼ぶ。

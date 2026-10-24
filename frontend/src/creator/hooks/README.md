# creator/hooks（操作層）

作る人のボタン・操作に対する処理。状態管理、IndexedDB、Geolocation、ジョブのポーリングなど。

- 通信は `shared/api/` を呼ぶ。fetch は直書きしない。
- 見た目は持たない。戻り値（状態とハンドラ）を `pages/` が components に渡す。

# shared/lib

React に依存しない小さなユーティリティと定数。

- `constants.ts`: 曲がる方向の表示文・矢印、ポーリング間隔、作成ジョブの段階名、送信写真の大きさなど
- `datetime.ts`: オフセット付き ISO 8601 と一覧用の日時表示
- `image.ts`: 写真を送信用 JPEG（長辺 1280px、EXIF の向きを反映）にする。大きさの計算は `fitWithin`
- 今後: `geo.ts`（turf.js を使う距離・方位・ポリライン距離）

依存: `shared/types/` のみ。

# follower/components（UI 層）

参加者の画面の見た目。参加者専用の部品を置く。
写真列の表示そのものは `shared/components/RoutePlanViewer` を使う。

- `EntryForm.tsx`: 入口画面。QR 読み取りボタンと ID 入力
- `QrScanner.tsx`: QR 読み取り中のカメラ映像と枠
- `NavigateHeader.tsx`: ロゴ、タイトル、出発地 → 目的地、案内 ID
- 今後: `OvershootAlert.tsx`（通り過ぎ・経路外れ警告）

- props だけで動く。状態・通信・位置情報は持たない。

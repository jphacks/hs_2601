# follower/hooks（操作層）

参加者側の処理。

- `useRoutePlan.ts`: 公開済み写真列の取得（画面を開いたときに 1 回）
- `useQrScanner.ts`: getUserMedia のカメラ映像から jsQR で QR を読む。見つけたら止めてカメラを解放
- 今後: `useWatchPosition.ts`、`useStepProgress.ts`、`usePreloadImages.ts`

- 判定ロジックは `follower/logic/` の純関数を呼ぶ。
- 通信は `shared/api/endpoints.ts` を呼ぶ。fetch は直書きしない。

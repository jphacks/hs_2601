# creator/components（UI 層）

作る人の画面の見た目。props で値とコールバックを受け取り、描くだけ。

- `CreatorLayout.tsx`: 全画面共通の枠とヘッダー
- `CreatorHome.tsx`: ホーム（2 ボタン）
- `RouteCreateForm.tsx` + `PhotoGrid.tsx`: 命名・出発地・目的地入力と目印写真の一覧（位置情報の状態と取り直し）
- `RouteLoading.tsx`: 作成中（処理段階の表示）
- `RouteDetail.tsx`: 作成結果の確認。写真列は `shared/components/RoutePlanViewer` で描く
- `RoutePublishList.tsx`: 道の一覧（チェックで選択）
- `RoutePublished.tsx`: 公開完了（名前・ID・URL とコピー・QR 画像）
- `styles.ts`: 共通のボタン・入力欄クラス

- 状態（useState）、通信（fetch）、ブラウザ API（カメラ・位置情報）は持たない。
  例外は `<input type="file">` を開くための useRef だけ。
- それらは `creator/hooks/` が担い、`creator/pages/` が繋ぐ。

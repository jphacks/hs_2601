# creator/components（UI 層）

作る人の画面の見た目。props で値とコールバックを受け取り、描くだけ。

- 状態（useState）、通信（fetch）、ブラウザ API（カメラ・位置情報）は持たない。
- それらは `creator/hooks/` が担い、`creator/pages/` が繋ぐ。

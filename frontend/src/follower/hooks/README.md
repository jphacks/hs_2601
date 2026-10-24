# follower/hooks（操作層）

参加者側の処理。`watchPosition` による位置追跡、現在ステップの更新、画像の先読みなど。

- 判定ロジックは `follower/logic/` の純関数を呼ぶ。
- 通信は `shared/api/` を呼ぶ。

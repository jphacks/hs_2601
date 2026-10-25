# shared/hooks

creator / follower の両方で使う、画面に依存しない小さな React hooks。

- `useAsync.ts`: ID が決まったら 1 回だけ取得して loading / error / ready を返す

- 通信そのものは持たない。呼び出し側が `shared/api/endpoints.ts` の関数を渡す。

# frontend

Web フロントエンド（Vite + React + TypeScript）。
作る人（`/c/*`）と参加者（`/r/:id`）を 1 アプリ内でパスで分ける。

## 起動

```bash
npm install
npm run dev
```

- 作る人: http://localhost:5173/c
- 参加者: http://localhost:5173/r/sample

## 構成

```
src/
├── main.tsx        # エントリ
├── index.css       # 全体スタイル
├── app/router.tsx  # ルーティング（/c → creator、/r/:id → follower）
├── shared/         # 両者共通（型・API クライアント・共用 UI）
├── creator/        # 作る人の画面・ロジック
└── follower/       # 参加者の画面・ロジック
```

依存は `creator/` → `shared/`、`follower/` → `shared/` の一方向のみ。
詳細な構成案: [docs/directory-structure.md](../docs/directory-structure.md)

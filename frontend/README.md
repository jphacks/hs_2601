# frontend

Web フロントエンド（Vite + React + TypeScript）。
作る人（`/c/*`）と参加者（`/r/:id`）を 1 アプリ内でパスで分ける。

## 起動と画面確認

```bash
npm install     # 初回のみ
npm run dev
```

| URL | 期待する表示 |
|---|---|
| http://localhost:5173/ | `/c` にリダイレクト |
| http://localhost:5173/c | 「作る人」の見出し |
| http://localhost:5173/r/sample | 「参加者」「道案内 ID: sample」 |

スマホからは、起動時に表示される `Network:` の URL を同じ Wi-Fi で開く。
バックエンドの URL を変える場合は `.env.example` をコピーして `.env.local` を作る。

## 構成

```
src/
├── main.tsx            # エントリ
├── index.css           # 全体スタイル
├── app/router.tsx      # ルーティング（/c → creator、/r/:id → follower）
├── shared/             # 両者共通
│   ├── api/            #   通信層: client.ts（fetch ラッパー）、endpoints.ts（予定）
│   ├── types/          #   写真列 JSON などの型（backend/schemas と 1:1）
│   └── components/     #   共用 UI（RoutePlanViewer など）
├── creator/            # 作る人（/c/*）
│   ├── pages/          #   hooks と components を繋ぐだけの薄いファイル
│   ├── components/     #   UI 層: 見た目のみ
│   └── hooks/          #   操作層: 状態・ブラウザ API・ポーリング
└── follower/           # 参加者（/r/:id）
    ├── pages/
    ├── components/     #   UI 層
    ├── hooks/          #   操作層
    └── logic/          #   位置判定の純関数
```

## 3 層の分離

| 層 | 場所 | 触る人 |
|---|---|---|
| UI（見た目） | `*/components/` | UI 担当 |
| 操作（状態・ハンドラ） | `*/hooks/`、`follower/logic/` | ロジック担当 |
| 通信（バックエンド） | `shared/api/`、`shared/types/` | 通信担当 |

`pages/` は 3 層を繋ぐだけに留め、ロジックや見た目を書かない。
依存は `creator/` → `shared/`、`follower/` → `shared/` の一方向のみ。
詳細な構成案: [docs/directory-structure.md](../docs/directory-structure.md)

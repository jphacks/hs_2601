# frontend

Web フロントエンド（Vite + React + TypeScript）。
作る人（`/c/*`）と参加者（`/r/:id`）を 1 アプリ内でパスで分ける。

## 起動と画面確認

```bash
npm install     # 初回のみ
npm run dev
npm test        # vitest（通信層・検証ロジックの単体テスト）
npm run lint    # oxlint（creator ⇄ follower の import 禁止も検査）
```

バックエンド未接続の間は **fixture モード**（既定）で動く。写真列は
`src/shared/fixtures/sampleRoutePlan.json`（`backend/out/cases/5` を publish したもの）を返し、
作成・公開はブラウザのメモリ上だけで完結する（リロードで消える）。

| URL | 期待する表示 |
|---|---|
| http://localhost:5173/ | `/c` にリダイレクト |
| http://localhost:5173/c | 作る人のホーム（「道を作る」「作った道を公開する」） |
| http://localhost:5173/c/routes | 一覧。サンプル「四天王寺 南大門 → 天王寺公園 てんしば」が公開済みで入っている |
| http://localhost:5173/r | 参加者の入口。案内 ID を入力するか「サンプルの道案内を開く」を押す |
| http://localhost:5173/r/7298a7dd6554 | 参加者画面。サンプルの写真列が 9 ステップ表示される |

バックエンドに繋ぐときは `.env.local` に `VITE_API_MODE=server` を書く（`.env.example` 参照）。

スマホからは、起動時に表示される `Network:` の URL を同じ Wi-Fi で開く。
バックエンドの URL を変える場合は `.env.example` をコピーして `.env.local` を作る。

## 構成

```
src/
├── index.css           # Tailwind の読み込みと参加者画面の配色トークン
├── app/
│   ├── main.tsx        #   エントリ
│   └── router.tsx      #   ルーティング（/c/* → creator、/r/:id → follower）
├── shared/             # 両者共通
│   ├── api/            #   通信層: endpoints.ts（入口）、fixtureApi.ts / serverApi.ts、client.ts
│   ├── types/          #   写真列 JSON などの型（backend/app/schemas と 1:1）
│   ├── fixtures/       #   バックエンドなしで動かすサンプル（sampleRoutePlan.json）
│   ├── components/     #   共用 UI: RoutePlanViewer、StepView
│   ├── hooks/          #   useAsync
│   └── lib/            #   定数
├── creator/            # 作る人（/c/*）
│   ├── pages/          #   URL ごとの画面。hooks と components を繋ぐだけ
│   ├── components/     #   UI 層: 見た目のみ
│   ├── hooks/          #   操作層: 入力・撮影・ポーリング・一覧・公開
│   └── storage/        #   localStorage の作成者 ID
└── follower/           # 参加者（/r/:id）
    ├── pages/          #   NavigatePage
    ├── components/     #   UI 層: NavigateHeader
    ├── hooks/          #   操作層: useRoutePlan
    └── logic/          #   位置判定の純関数（未着手）
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

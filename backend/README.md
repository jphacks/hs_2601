# backend

API サーバー（FastAPI / Python）。

## 起動

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

- 疎通確認: http://localhost:8000/health
- API ドキュメント: http://localhost:8000/docs

## テスト

```bash
pip install pytest httpx
pytest
```

## 構成

```
app/
├── main.py              # アプリ生成、CORS、ルーター登録
├── api/
│   ├── creator.py       # 作る人向け API（作成受付 / ステータス / 一覧 / 公開）
│   └── follower.py      # 参加者向け API（公開済み詳細取得）
├── schemas/             # Pydantic モデル（写真列 JSON など）
└── services/
    ├── creator/         # 作成ジョブのロジック
    └── follower/        # 公開済み取得のロジック
```

`api/` はルーティングと入出力変換だけを行い、処理は `services/` に置く。
詳細な構成案: [docs/directory-structure.md](../docs/directory-structure.md)

# backend

API サーバー（FastAPI / Python）。

## 起動と疎通確認

```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate   # 初回のみ
pip install -r requirements.txt                       # 初回のみ
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

| URL | 期待する表示 |
|---|---|
| http://localhost:8000/health | `{"status":"ok"}` |
| http://localhost:8000/docs | Swagger UI（API 一覧） |

コマンドラインから確認する場合:

```bash
curl http://localhost:8000/health
```

## テスト

```bash
pip install pytest httpx
pytest
```

ROS など別環境が `PYTHONPATH` に入っている PC でも動くよう、`pytest.ini` でそれらの pytest プラグインを無効化している。

## 経路探索の確認

仕様と進捗: [docs/route-exploration.md](../docs/route-exploration.md)

### ステップ 1: 中間形式と設定

```bash
python -c "
from app.schemas.exploration import Exploration
e = Exploration.model_validate_json(open('tests/fixtures/route_sample.json', encoding='utf-8').read())
print(len(e.points), e.points[0].turn)
"
```

### ステップ 2: Geocoding（地名 → 座標）

Google Geocoding API に地名を渡すと、緯度経度と正式な住所が返る。
`external/google/geocoding.py` が API を叩き、`services/creator/geocode.py` が中間形式の `Place` に変換する。

```bash
# 1. API キーを設定する（初回のみ）
cp .env.example .env          # GOOGLE_MAPS_API_KEY= にキーを記入

# 2. 地名を座標にして地図に出す
python -m scripts.geocode "大阪駅" "グランフロント大阪" --out ./out

# 3. キーがまだ無いときは、保存済みレスポンスから描画できる
python -m scripts.geocode --fixture tests/fixtures/geocode_sample.json --out ./out
```

出力:

| ファイル | 内容 |
|---|---|
| `out/geocode.json` | 座標の一覧（`Place` の配列） |
| `out/raw/geocode.json` | API の生レスポンス。fixture として再利用できる |
| `out/map.html` | **ブラウザで開く。** 地名ごとのピンと、下部に JSON を表示 |

`out/map.html` は Leaflet + 地理院タイル（国土地理院）で描くので、表示に API キーは不要。
ピンをクリックすると正式住所と座標が出る。開き方は `explorer.exe out/map.html`（WSL）。

画像にして共有したいときは、Firefox があれば次で `out/map.png` ができる。

```bash
python -m scripts.snapshot_map --out ./out
```

Geocoding API の挙動:

- `language=ja`、`region=jp` を付けて日本語・日本優先で検索している。
- 結果が複数あるときは先頭 1 件を採用する。曖昧な地名（例: 「中央駅」）は意図と違う場所になるので、都市名や施設名を添える。
- `status` が `ZERO_RESULTS`（該当なし）や `REQUEST_DENIED`（キーの問題）のときは `GeocodingError` を投げる。

### ステップ 3: Routes API（徒歩経路）

出発地・目的地（と経由地）の座標を Routes API に POST すると、徒歩経路のポリラインと、
曲がり角ごとのステップ（座標・maneuver・案内文・距離）が返る。
`external/google/routes.py` が API を叩き、`services/creator/route.py` が `Place` から呼べる形にする。

```bash
# 出発地 → 目的地
python -m scripts.route "大阪駅" "グランフロント大阪" --out ./out

# 経由地あり（作成者が写真を撮った地点を想定。2 つ以上なら順序を自動最適化）
python -m scripts.route "大阪駅" "グランフロント大阪" --via "梅田スカイビル" --out ./out

# キー無しで再描画（保存済みの raw/*.json から）
python -m scripts.route --from-raw ./out --out ./out
```

出力:

| ファイル | 内容 |
|---|---|
| `out/raw/routes.json` | Routes API の生レスポンス。fixture として再利用できる |
| `out/route_preview.json` | ステップ一覧の簡易形式（確認用） |
| `out/map.html` | 経路線（青）とステップのピン。S = 出発、G = 目的地、青 = 直進系、橙 = 左折、紫 = 右折。ピンをクリックで案内文 |

Routes API の挙動:

- Geocoding と違い POST で、キーは `X-Goog-Api-Key` ヘッダー、欲しい項目は `X-Goog-FieldMask` ヘッダーで指定する。
- 駅構内など屋内区間のステップは `navigationInstruction` が無く、案内文・maneuver が空になる。
- `routes` が空、または HTTP 403（API 未有効化・キー制限）は `RoutesError` になる。

## 構成

```
app/
├── main.py              # アプリ生成、CORS、ルーター登録
├── core/
│   └── config.py        # .env / 環境変数の読み込み（get_settings()）
├── api/
│   ├── creator.py       # 作る人向け API（作成受付 / ステータス / 一覧 / 公開）
│   └── follower.py      # 参加者向け API（公開済み詳細取得）
├── schemas/
│   └── exploration.py   # 経路探索の中間形式 route.json（内部用）
├── external/
│   └── google/
│       ├── geocoding.py # Geocoding API クライアント
│       └── routes.py    # Routes API クライアント
└── services/
    ├── creator/
    │   ├── geocode.py   # ステップ 2: 地名 → Place
    │   ├── route.py     # ステップ 3: 徒歩経路、ポリライン復号
    │   └── mapview.py   # 確認用の地図 HTML（Leaflet + 地理院タイル）
    └── follower/
scripts/
├── geocode.py           # ステップ 2 の確認コマンド
├── route.py             # ステップ 3 の確認コマンド
└── snapshot_map.py      # out/map.html を PNG にする（Firefox 使用）
tests/
├── fixtures/            # route_sample.json、geocode_sample.json、routes_sample.json（実レスポンス）
└── test_*.py
```

`api/` はルーティングと入出力変換だけを行い、処理は `services/` に置く。
外部 API の呼び出しは `external/` に閉じ込め、`services/` から呼ぶ。
詳細な構成案: [docs/directory-structure.md](../docs/directory-structure.md)

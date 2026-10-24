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

画像にして共有したいときは、Firefox があれば次で `out/map.png` と `out/contact.png` ができる。

```bash
python -m scripts.snapshot_map --out ./out             # 両方
python -m scripts.snapshot_map --out ./out --only map  # 地図だけ
python -m scripts.explore_route "出発地" "目的地" --png   # 一括実行と同時に出す
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

### ステップ 4: 曲がり角抽出（中間形式 route.json の生成）

Routes API のステップ境界を候補にし、採用・不採用を判定して `route.json` を作る。
ロジックの詳細は [docs/route-exploration.md](../docs/route-exploration.md) 4 章。

```bash
python -m scripts.turns "大阪駅" "グランフロント大阪" --out ./out
python -m scripts.turns --from-raw ./out --out ./out     # キー無しで再判定（しきい値調整に使う）
```

出力:

| ファイル | 内容 |
|---|---|
| `out/route.json` | 中間形式。画像は null（ステップ 5 で埋める） |
| `out/map.html` | 採用点を色分け（緑 = 出発、青 = 直進、橙 = 左、紫 = 右、赤 = 目的地）、不採用点を灰色 ×。クリックで判定理由と方位差 |

ターミナルにも候補ごとの判定一覧が出る。しきい値は `app/services/creator/turns.py` 冒頭の定数。

### ステップ 5: Street View 画像の取得（候補を複数）

`route.json` の各点について、向き・位置・画角の違う **候補画像を 8 枚**（重複は除去）取り、`candidates` に入れる。出発点・目的地は向きの違いが無いので位置をずらして 8 枚にする。
`image` には先頭候補を仮採用し、ステップ 7 で VLM が選び直す。`--single` で従来どおり 1 枚だけ取ることもできる。

```bash
python -m scripts.streetview --from-route ./out/cases/4                 # route.json を読み、画像を付けて上書き
python -m scripts.streetview --from-route ./out/cases/4 --offset-m 10 --fov 100
python -m scripts.streetview --from-route ./out/cases/4 --no-prefer-official
python -m scripts.streetview --from-route ./out/cases/4 --heading approach   # カメラの向きを変える
```

出力（指定ディレクトリ内）:

| ファイル | 内容 |
|---|---|
| `route.json` | `image` / `image_source` / `street_view`（pano_id、撮影年月、公式か投稿か、手前何 m か）が埋まる |
| `images/NNN.jpg` | 640×640 の画像 |
| `contact.html` | **画像一覧。** 経路順にカードで並び、曲がる方向・案内文・撮影情報を表示 |
| `map.html` | ピンをクリックで画像 |

カメラの向き（`--heading`）:

| モード | 向き | 向く場面 |
|---|---|---|
| `bisector`（既定） | 進入方向と退出方向の中間 | 直進方向と曲がる先の道の両方が枠に入る |
| `approach` | 進入方向 | まっすぐ先の目印を大きく写したいとき。曲がる先は枠外になりやすい |
| `departure` | 退出方向 | 入る道を正面に写す |

パノラマの選び方:

- Metadata API（無料）で候補を探し、見つかれば Static API で画像を取る。
- **Google 公式撮影を優先する。** 最寄りがユーザー投稿なら 8 m ずつ手前に下がって最大 4 回探し、公式が無ければ最初の候補を使う。
  ユーザー投稿には夜景・屋内・船上など案内に使えない画像が多いため。出発点だけは前方に探す。
- 画像が無い地点（公園内の小道など）は `image` を null のままにする。
- 作成者の写真（`image_source == creator_photo`）は触らない。

### ステップ 6: 一括実行（中間発表のデモ素材）

出発地と目的地を渡すだけで、ステップ 2〜5 を順に実行する。

```bash
python -m scripts.explore_route "大阪駅" "グランフロント大阪" --out ./out
python -m scripts.explore_route "大阪駅" "グランフロント大阪" --via "梅田スカイビル" --out ./out
explorer.exe out/contact.html     # 画像一覧
explorer.exe out/map.html         # 地図
```

ステップ 5 のオプション（`--heading`、`--fov`、`--pitch`、`--offset-m`）はそのまま使える。

#### キャッシュ

外部 API のレスポンスは `backend/.cache/google/` に保存し、同じ入力なら API を叩かない。

| 対象 | キー |
|---|---|
| Geocoding | 地名 |
| Routes | 出発地・経由地・目的地の座標の組 |
| Street View 画像 | パノラマ ID、向き、画角、ピッチ、サイズ |

- 失効はしない。最新を取り直したいときは `--no-cache` を付けるか、`backend/.cache/` を削除する。
- Street View の Metadata API（無料）は毎回叩く。パノラマの選択は常に最新の結果で行う。
- `.cache/` は git 管理外。

### ステップ 7: VLM による採点と目印文（Gemini / Claude）

候補画像を VLM に渡し、「目印のわかりやすさ」「どこで曲がるかのわかりやすさ」「矢印の描きやすさ」を 1〜5 で採点させて最良の 1 枚を採用し、目印の短い文章を `landmark` に、矢印の経路（画像内座標）を `candidates[].score.arrow_path` に入れる。

```bash
# .env に GEMINI_API_KEY（Google AI Studio、無料枠）を書いておく
python -m scripts.landmark --from-route ./out/cases/4
python -m scripts.landmark --from-route ./out/cases/4 --no-vlm     # VLM を使わずフォールバック文だけ
```

出力: `route.json`（`candidates[].score`、`chosen_candidate`、`image`、`landmark` が埋まる）、`contact.html`（各候補の点数つき。採用した候補は青枠）。

- 1 地点につき VLM を 1 回呼び、全候補を一度に渡す。結果は画像のハッシュ + プロンプト + モデル名でキャッシュする。
- 既定は Gemini（`VLM_PROVIDER=gemini`、`VLM_MODEL=gemini-3.5-flash-lite`）。Claude にするには `VLM_PROVIDER=claude` と `ANTHROPIC_API_KEY`。
- 無料枠の 1 分あたり上限を避けるため、呼び出し間隔を `VLM_MIN_INTERVAL_S`（既定 4 秒）空ける。429 は待って再試行する。
- VLM が失敗した地点や候補が無い地点は、案内文と距離からのフォールバック文になる（処理は止めない）。
- プロンプト: `app/external/vlm/prompts/evaluate.txt`

`scripts.explore_route` はステップ 7 まで含めて一括実行する（キーが無ければフォールバックのみ、`--no-vlm` で明示的に省略）。

### ステップ 8: 矢印の描画

採用画像に、VLM が返した経路に沿って曲線の矢印を重ね、`arrow_image` に入れる。API 不要。

```bash
python -m scripts.arrow --from-route ./out/cases/4
```

- 色: 左 橙 / 右 紫 / 直進 青 / 到着 赤。白縁つきで写真の上でも読める。
- 左右折なのに経路が曲がっていなければ、終点をその側へ寄せて必ず曲線にする。
- VLM の経路が無い地点は turn ごとの既定形で描く。
- `contact.html` と `map.html` は矢印入り画像を優先して表示する。`scripts.explore_route` はここまで一括で実行する。

## 構成

```
app/
├── main.py              # アプリ生成、CORS、ルーター登録
├── core/
│   └── config.py        # .env / 環境変数の読み込み（get_settings()）。out_dir、cache_dir
├── api/
│   ├── creator.py       # 作る人向け API（作成受付 / ステータス / 一覧 / 公開）
│   └── follower.py      # 参加者向け API（公開済み詳細取得）
├── schemas/
│   └── exploration.py   # 経路探索の中間形式 route.json（内部用）
├── external/
│   └── google/
│       ├── geocoding.py   # Geocoding API クライアント
│       ├── routes.py      # Routes API クライアント
│       └── street_view.py # Street View Metadata / Static API クライアント
├── imaging/
│   └── arrow.py         # 曲線の矢印を描く（Pillow、純粋な描画）
├── external/vlm/
│   ├── base.py          # VLM 共通インターフェース、返答 JSON の解釈
│   ├── gemini.py        # Gemini API（REST、429 再試行）
│   ├── claude.py        # Claude API（REST）
│   ├── factory.py       # .env の設定からクライアントを作る
│   └── prompts/evaluate.txt  # 採点プロンプト
└── services/
    ├── creator/
    │   ├── geocode.py   # ステップ 2: 地名 → Place
    │   ├── route.py     # ステップ 3: 徒歩経路、ポリライン復号
    │   ├── geo.py       # 方位・距離の純関数
    │   ├── turns.py     # ステップ 4: 曲がり角抽出 → route.json
    │   ├── streetview.py # ステップ 5: 画像取得（公式パノラマ優先、候補を複数）
    │   ├── landmark.py  # ステップ 7: VLM 採点 → 1 枚選定 → 目印文・矢印経路
    │   ├── arrow.py     # ステップ 8: 矢印入り画像
    │   ├── cache.py     # 外部 API レスポンスのファイルキャッシュ
    │   ├── contact.py   # 確認用の画像一覧 HTML
    │   └── mapview.py   # 確認用の地図 HTML（Leaflet + 地理院タイル）
    └── follower/
scripts/
├── geocode.py           # ステップ 2 の確認コマンド
├── route.py             # ステップ 3 の確認コマンド
├── turns.py             # ステップ 4 の確認コマンド
├── streetview.py        # ステップ 5 の確認コマンド
├── landmark.py          # ステップ 7 の確認コマンド
├── arrow.py             # ステップ 8 の確認コマンド
├── explore_route.py     # ステップ 6: 2〜8 の一括実行
└── snapshot_map.py      # out/map.html を PNG にする（Firefox 使用）
tests/
├── fixtures/            # route_sample.json、geocode_sample.json、routes_sample.json（実レスポンス）
└── test_*.py
```

`api/` はルーティングと入出力変換だけを行い、処理は `services/` に置く。
外部 API の呼び出しは `external/` に閉じ込め、`services/` から呼ぶ。
詳細な構成案: [docs/directory-structure.md](../docs/directory-structure.md)

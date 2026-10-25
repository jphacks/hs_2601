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

Firefox があれば、`map.html` / `contact.html` を書き換えるスクリプト（`explore_route`、`streetview`、`landmark`、`arrow`）は
同じ場所の `map.png` と `contact.png` も毎回更新する。省略したいときは `--no-png`。手動で作り直すときは次。

```bash
python -m scripts.snapshot_map --out ./out             # 両方
python -m scripts.snapshot_map --out ./out --only map  # 地図だけ
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
| `route.json` | `image` / `image_source` / `street_view`（pano_id、撮影年月、公式か投稿か、手前何 m か、パノラマの緯度経度）が埋まる |
| `images/NNN.jpg` | 640×640 の画像 |
| `images/NNN_arrow.png` | ステップ 8 で作る矢印入り画像（PNG、劣化なし） |
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

候補画像を VLM に渡し、まず「撮影地点に歩行者が立てるか」「進む先の路面へ歩いて行けるか（柵・階段・水面で遮られていないか）」で船上・店内・階段の踊り場などを除外し、残りを「現在地のわかりやすさ」「矢印の引きやすさ（どこを曲がるのかがはっきり見えるか）」で 1〜5 採点して最良の 1 枚を採用し、目印の短い文章を `landmark` に、矢印用の点列（現在地 → 今の道 → 通りたい道 に沿って等間隔、画像内座標）を `candidates[].score.arrow_path` に入れる。

```bash
# .env に GEMINI_API_KEY（Google AI Studio、無料枠）を書いておく
python -m scripts.landmark --from-route ./out/cases/4
python -m scripts.landmark --from-route ./out/cases/4 --no-vlm     # VLM を使わずフォールバック文だけ
```

出力: `route.json`（`candidates[].score`、`chosen_candidate`、`image`、`landmark` が埋まる）、`contact.html`（各候補の点数つき。採用した候補は青枠）。

- 1 地点につき VLM を 1 回呼び、全候補を一度に渡す。結果は画像のハッシュ + プロンプト + モデル名でキャッシュする。
- 既定は Gemini（`VLM_PROVIDER=gemini`、`VLM_MODEL=gemini-3.5-flash`）。Claude にするには `VLM_PROVIDER=claude` と `ANTHROPIC_API_KEY`。
- 無料枠の 1 分あたり上限を避けるため、呼び出し間隔を `VLM_MIN_INTERVAL_S`（既定 4 秒）空ける。429 と 503 は待って再試行する。
- VLM が失敗した地点や候補が無い地点は、案内文と距離からのフォールバック文になる（処理は止めない）。
- プロンプト: `app/external/vlm/prompts/evaluate.txt`。画像だけでなく、経路情報と各候補の「どこからどの向きで見ているか」を文章で添える（`services/creator/vlm_context.py`）:
  - 経路情報: 地点の緯度経度（小数 6 桁）、進入・退出方位（度と八方位）、向きの変化（右 35° など）、交差点の 60 m 手前〜40 m 先の経路の座標と進行方位。
  - 各候補: 撮影位置の緯度経度と交差点との位置関係（手前 9 m / 曲がった先 8 m）、カメラの方位・進入方位から見た向き・画角・ピッチ、公式か投稿か、撮影年月、
    曲がる地点の画像内座標、経路の投影線（ステップ 8 と同じ計算）。
  - VLM には投影線を「歩行者が実際に歩く線」として信頼させ、目印は曲がる地点の近く・曲がる側から選ばせる。`arrow_path` は投影線がある画像ではそのまま写させる。
  - プロンプトが変わったので、古い `.cache/` の結果は使われず再評価される。
- 採用候補の決め方: まず歩ける候補（`on_walkway`）に絞り、次に経路の幾何（ステップ 8 と同じ投影）で
  「道なりの経路が画像に見える → Google 公式撮影 → 曲がり角まで見える → 足元から始まる」の順に最良のものだけ残し、
  その中にモデルの選択があればそれ、無ければ点数で選ぶ。歩行者の視点で曲がり角を見下ろす候補が選ばれやすくなる。

`scripts.explore_route` はステップ 7 まで含めて一括実行する（キーが無ければフォールバックのみ、`--no-vlm` で明示的に省略）。

### ステップ 8: 矢印の描画

採用画像に、経路（道路の中心線）をカメラから見た形に投影した点列を矢印として重ね、`arrow_image` に入れる。API 不要。

```bash
python -m scripts.arrow --from-route ./out/cases/4
python -m scripts.arrow --from-route ./out/cases/4 --source vlm   # 旧方式: VLM が打った点を使う
```

- 点列の作り方（`services/creator/arrow_geo.py`、`imaging/projection.py`）:
  1. パノラマの位置（`street_view.lat/lng`）・向き（`heading`）・画角（`fov`）・ピッチからカメラを置く。地上高 2.5 m のピンホールと見なす。
  2. 曲がり角の 60 m 手前〜40 m 先の経路を 2 m ごとに刻み、各点を地面として画像座標に投影する。
  3. 画像に入る連続区間のうち、奥へ進んでいて曲がり角を含むものを選ぶ。カメラが後ろ向き・経路が映らない画像なら投影は諦める。
  4. 経路がカメラの脇を通って枠外から入ってくる場合は枠の縁から線を始め、足元（画面中央下）を通るなら足元から伸ばす。
  5. Douglas-Peucker で直線上の点と消失点付近の小さなブレを落とす。
- 投影できない地点は VLM の点列（`candidates[].score.arrow_path`）、それも無ければ turn ごとの既定形で描く。実行ログの `投影 x / VLM y` で内訳が分かる。
- 色: 左 橙 / 右 紫 / 直進 青 / 到着 赤。単色で縁取りなし。
- 既知の限界: 広場や公園では経路のポリラインが粗く、投影した線が実際の歩道からずれることがある。
  パノラマの位置が無い古い `route.json` は `offset_m` から位置を推定する（精度は落ちる）。
- `contact.html` と `map.html` は矢印入り画像を優先して表示する。`scripts.explore_route` はここまで一括で実行する。

### ステップ 9: 写真列の保存（Supabase、命名をキーに）

出力ディレクトリの写真列（矢印入り画像 + 地点情報）を、命名をキーにして Supabase に保存する。
DB は Postgres のテーブル `route_plans`、画像は公開バケット `plans`。参加者向けの公開形式は `app/schemas/route_plan.py`。

```bash
# 初回のみ: Supabase にログインしてプロジェクトを紐づけ、テーブルとバケットを作る
supabase login
supabase link --project-ref <project-ref>        # リポジトリ直下で実行
supabase db push --linked                        # supabase/migrations/ を適用

# .env に SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY / SUPABASE_ANON_KEY を書く（.env.example 参照）
python -m scripts.publish --from-route ./out/cases/5 --name "四天王寺→てんしば"           # 出力済みのディレクトリを保存
python -m scripts.explore_route "四天王寺 南大門" "天王寺公園 てんしば" --out ./out/cases/5 --name "四天王寺→てんしば"   # 生成から保存まで一括
```

保存した写真列を確認する（参加者と同じ anon キーで読む）:

```bash
python -m scripts.show_plan --list                                   # 保存済み一覧
python -m scripts.show_plan --name "四天王寺→てんしば"                  # 地点と画像 URL
python -m scripts.show_plan --name "四天王寺→てんしば" --html ./out/plan.html && explorer.exe out/plan.html   # 画像を並べて見る
```

ブラウザで見るなら Supabase ダッシュボードの Table Editor（`route_plans`）と Storage（`plans` バケット）。

### ステップ 10: QR コード（参加者 URL）

契約は [docs/interface.md](../docs/interface.md)。参加者画面の URL は `{PUBLIC_BASE_URL}/r/<id>` で、QR はこれを符号化したもの。
`.env` に `PUBLIC_BASE_URL` があれば、`scripts.publish` と `scripts.explore_route --name` が `<dir>/qr.png` を出す。
フロントのデプロイ前は `http://localhost:5173`（Vite の開発サーバー）で良く、デプロイ後に差し替えて保存し直す。

参加者の流れ（QR を読む → URL → id → anon キーで取得 → 表示）はバックエンドだけで確認できる:

```bash
python -m scripts.show_plan --qr ./out/cases/5/qr.png --html ./out/cases/5/plan.html   # スマホの代わりに QR を読んで取得
pytest                     # モック版（tests/test_follower_flow.py）。外部に出ない
pytest -m live             # 実際の Supabase を叩く版（保存済みの「四天王寺→てんしば」を QR 経由で取得し、画像も取る）
```

QR の生成は `segno`、読み取り（テスト・確認用）は `zxing-cpp`。参加者側のロジックは `app/services/follower/`。

### ステップ 11: 外部のスマホで QR → 写真列を通す（backend だけで完結）

フロント無しでも、API サーバーが `/r/<id>` で写真列の HTML を返す（`app/api/follower.py`）。
開発 PC を Cloudflare Tunnel で HTTPS 公開し、その URL を QR にすればスマホで開ける（トンネルの詳しい使い方とフロント側の手順は [docs/tunnel.md](../docs/tunnel.md)）。

```bash
# 1. cloudflared を入れる（初回のみ。アカウント不要）
curl -L -o ~/.local/bin/cloudflared https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64
chmod +x ~/.local/bin/cloudflared

# 2. API サーバーを起動（端末 A）
uvicorn app.main:app --host 0.0.0.0 --port 8000

# 3. 公開 URL を発行（端末 B）。表示される https://xxxx.trycloudflare.com を控える
cloudflared tunnel --url http://localhost:8000

# 4. その URL を .env の PUBLIC_BASE_URL に書き、QR を作り直す（端末 C）
python -m scripts.publish --from-route ./out/cases/5 --name "四天王寺→てんしば"
explorer.exe out/cases/5/qr.png

# 5. スマホの標準カメラで qr.png を読む → https://xxxx.trycloudflare.com/r/<id> が開き、写真列が表示される
```

- 一時 URL は `cloudflared` を起動し直すたびに変わる。変わったら 4 をやり直す。
- 確認用の HTML（`app/services/follower/view.py`）は画像を縦に並べるだけ。本番の参加者画面はフロントが `GET /api/public/routes/<id>` か Supabase 直読みで作る（docs/interface.md）。
- サーバー側の確認: `curl -s http://localhost:8000/r/<id> | grep -c "<img"` が地点数と一致すれば OK。

| 出力 | 内容 |
|---|---|
| `route_plans` の 1 行 | `id`（命名の SHA-256 先頭 12 桁）、`name`、`status`、`plan_json`（ステップ配列 + ポリライン） |
| `plans/<id>/NNN.png` / `NNN.jpg` | 矢印入り画像（PNG）。無い地点は採用画像（JPEG）。公開 URL が `plan_json.steps[].image_url` に入る |
| `<dir>/published.json` | 保存内容の控え |

- **同じ `--name` で実行し直すと同じ ID に上書きされる。** 別の道案内として残したいときは名前を変えるか `--id` を指定する。
- 参加者側は anon キーで `GET {SUPABASE_URL}/rest/v1/route_plans?id=eq.<id>` か `?name=eq.<名前>` を叩けば読める（RLS で `status = 'published'` の行だけ）。画像 URL は認証なしで開ける。
- 書き込みは service_role キーだけ。フロントに渡さない。
- SDK は使わず、`app/external/supabase/rest.py` が PostgREST と Storage の REST を httpx で叩く。

### ステップ 12: 作成者の写真を通る経路（photos.json から）

作る人が撮った写真列（画像 + 座標、撮った順）を入力にし、「出発地 → 写真 1 → … → 写真 n → 目的地」を通る経路を作る。
入力の形は [docs/interface.md](../docs/interface.md) 4 章（`photos.json`、型は `app/schemas/creator_input.py`）。

```bash
# テスト用の写真を Street View で作る（作成者が曲がり角で撮った想定。写真の座標はパノラマの撮影位置）
python -m scripts.fake_photos "四天王寺 南大門" "天王寺公園 てんしば" --n 3 --out ./out/cases/6 --name "写真つき→てんしば"
python -m scripts.photos_map --input ./out/cases/6           # 写真順の地図（photos_map.html）で順序を目視

# 写真を通る経路を作り、保存と QR まで（--publish は photos.json の命名で保存。--name で上書き可）
python -m scripts.explore_route --photos ./out/cases/6 --out ./out/cases/6 --publish
python -m scripts.show_plan --qr ./out/cases/6/qr.png
```

仕組み:

- 区間（出発地→写真 1、写真 1→写真 2、…）ごとに既存の経路計算と曲がり角抽出を回し、区間の境界を写真地点 1 つに統合する（`app/services/creator/legs.py`）。
  写真の順序は入力順で固定。曲がる方向は「前区間の到着方位 → 次区間の出発方位」の差で決める。
- 写真地点は `image_source = "creator_photo"`。Street View 取得・VLM・矢印をすべて飛ばし、写真をそのまま使う。目印文は `caption` があればそれ。
- 写真の座標は `creator_photo` に残し、経路上の点は道路に吸着した座標。吸着が `accuracy_m` の 3 倍を超えると警告（処理は止めない）。
- 同じ場所の写真など経路が取れない区間は飛ばして警告に残し、その写真は前の写真に統合する。
- 出力は通常と同じ構成に `photos/`、`photos.json`、`legs/NN.json`（区間ごとの生レスポンス）、`photos_map.html` が加わる。

### ステップ 13: 作る人の HTTP API（フロントから作成・公開）

契約は [docs/interface.md](../docs/interface.md) 5 章。ステップ 12 と同じ処理（`app/services/creator/pipeline.py`、CLI と共通）を HTTP から回す。

```bash
# 0. 初回のみ: route_plans に creator_id 列を足す（supabase/migrations/20261025120000_route_plans_creator.sql）
#    未適用だと作成ジョブの保存と一覧が失敗する
# 1. 起動（GOOGLE_MAPS_API_KEY・SUPABASE_URL・SUPABASE_SERVICE_ROLE_KEY が必要。PUBLIC_BASE_URL は任意）
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 2. 作成受付（manifest = photos.json の中身、photos = <id>.jpg）。202 {"jobId", "routeId"}
curl -s -F "manifest=<./out/cases/6/photos.json" \
     $(for f in ./out/cases/6/photos/*.jpg; do printf -- '-F photos=@%s ' "$f"; done) \
     http://localhost:8000/api/routes
# 写真 0 枚なら manifest だけ（photos は [] にする）

# 3. 進み具合（state: running / done / failed、step: geocode / route / streetview / landmark / arrow / save）
curl -s http://localhost:8000/api/jobs/<jobId>

# 4. 一覧（作成者 ID 必須、新しい順）と詳細（下書きも見える）
curl -s "http://localhost:8000/api/routes?creator_id=<creator_id>"
curl -s http://localhost:8000/api/routes/<routeId>

# 5. 公開（status = published）と QR
curl -s -X POST http://localhost:8000/api/routes/<routeId>/publish
curl -s -o qr.png http://localhost:8000/api/routes/<routeId>/qr.png
```

仕組み:

- 受付時に manifest と写真ファイルを突き合わせ（過不足・開けない画像は 400）、写真は EXIF 回転・長辺 1280px の JPEG にして
  `out/routes/<routeId>/photos/` に、manifest を `photos.json` に置く（前回の出力は消す）。以降はこのディレクトリで処理する。
- 同じ命名が別の `creator_id` で保存済みなら 409（CLI で作った `creator_id` の無い行も別人扱い）。同じ道案内を作成中のときも 409。
- 処理はバックグラウンドのスレッドで走り、ジョブの状態はメモリに持つ（`app/services/creator/jobs.py`。再起動で消える）。
  終わると `status = "draft"` で保存され、公開 API で `published` になる。失敗時は利用者向けの文を `message` に入れ、詳細はサーバーログに出す。
- 参加者 URL は `{PUBLIC_BASE_URL}/r/{id}`。`PUBLIC_BASE_URL` が無ければこのサーバー自身の URL（`/r/{id}` の HTML 表示）にする。
- 依存（リポジトリ・ストレージ・パイプライン・ジョブ置き場・作業ディレクトリ）は `app/api/deps.py` にあり、
  テストは `app.dependency_overrides` でメモリ実装に差し替える（`tests/test_creator_api.py`）。

## 構成

```
app/
├── main.py              # アプリ生成、CORS、ルーター登録
├── core/
│   └── config.py        # .env / 環境変数の読み込み（get_settings()）。out_dir、cache_dir
├── api/
│   ├── creator.py       # 作る人向け API（作成受付 / ステータス / 一覧 / 公開）
│   ├── follower.py      # 参加者向け: GET /api/public/routes/{id}（JSON）、GET /r/{id}（HTML、QR の飛び先）
│   └── deps.py          # 依存関係（anon キーのリポジトリ）。テストで差し替える
├── schemas/
│   ├── creator_input.py # 作成入力 photos.json（PlanInput、CreatorPhoto）
│   ├── exploration.py   # 経路探索の中間形式 route.json（内部用）
│   └── route_plan.py    # 参加者に渡す公開形式（route_plans.plan_json）
├── external/
│   └── google/
│       ├── geocoding.py   # Geocoding API クライアント
│       ├── routes.py      # Routes API クライアント
│       └── street_view.py # Street View Metadata / Static API クライアント
├── imaging/
│   ├── arrow.py         # 矢印を描く（Pillow、純粋な描画）
│   ├── projection.py    # 地面の点をカメラ画像の座標に投影する（ピンホール）
│   └── qr.py            # QR の生成（segno）と読み取り（zxing-cpp）
├── external/supabase/
│   └── rest.py          # PostgREST / Storage クライアント（httpx）
├── repositories/
│   ├── base.py          # RoutePlanRepository / PhotoStorage のインターフェース
│   └── supabase_repo.py # Supabase 実装（テーブル route_plans、バケット plans）
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
│   ├── legs.py      # ステップ 12: 写真ごとの区間に分けて 3〜4 を回し、結合
│   ├── photos.py    # photos.json の読み込み、写真の正規化（EXIF 回転・縮小）
│   ├── photos_map.py # 写真順の地図
│   ├── fake_photos.py # テスト用: Street View で作成者写真を模倣
    │   ├── streetview.py # ステップ 5: 画像取得（公式パノラマ優先、候補を複数）
    │   ├── vlm_context.py # ステップ 7: 経路情報・撮影位置・投影線をプロンプト用の文章にする
    │   ├── landmark.py  # ステップ 7: VLM 採点 → 1 枚選定 → 目印文・矢印経路
    │   ├── arrow_geo.py # ステップ 8: 経路を画像に投影して道なりの点列を作る
    │   ├── arrow.py     # ステップ 8: 矢印入り画像（投影 → VLM → 既定形の順で点列を選ぶ）
│   ├── publish.py   # ステップ 9: 写真列を公開形式にして DB・ストレージへ保存
│   ├── qr.py        # ステップ 10: 参加者 URL の QR を qr.png に出す
    │   ├── cache.py     # 外部 API レスポンスのファイルキャッシュ
    │   ├── contact.py   # 確認用の画像一覧 HTML
    │   └── mapview.py   # 確認用の地図 HTML（Leaflet + 地理院タイル）
    └── follower/
        ├── fetch.py     # QR の URL → id → 写真列の取得（契約: docs/interface.md）
        └── view.py      # 確認用の表示 HTML（フロントの代わり）
scripts/
├── geocode.py           # ステップ 2 の確認コマンド
├── route.py             # ステップ 3 の確認コマンド
├── turns.py             # ステップ 4 の確認コマンド
├── streetview.py        # ステップ 5 の確認コマンド
├── landmark.py          # ステップ 7 の確認コマンド
├── arrow.py             # ステップ 8 の確認コマンド
├── publish.py           # ステップ 9: 命名をキーに Supabase へ保存
├── show_plan.py         # 確認用: 保存した写真列を anon キーで取り出す（一覧 / 詳細 / HTML）
├── explore_route.py     # ステップ 6: 2〜8 の一括実行（--name で 9 も、--photos で 12）
├── fake_photos.py       # ステップ 12: テスト用の写真列を作る
├── photos_map.py        # ステップ 12: 写真順の地図
└── snapshot_map.py      # out/map.html を PNG にする（Firefox 使用）
tests/
├── fixtures/            # route_sample.json、geocode_sample.json、routes_sample.json（実レスポンス）
└── test_*.py
```

`api/` はルーティングと入出力変換だけを行い、処理は `services/` に置く。
外部 API の呼び出しは `external/` に閉じ込め、`services/` から呼ぶ。
詳細な構成案: [docs/directory-structure.md](../docs/directory-structure.md)

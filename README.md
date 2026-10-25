# 会場までの道案内 作成アプリ　Wayfinder

[![IMAGE ALT TEXT HERE](https://jphacks.com/wp-content/uploads/2026/07/IMG_5316.png)](https://www.youtube.com/watch?v=piaNsc6ilBI)

## 製品概要
### 背景(製品開発のきっかけ、課題等）

目的地までの道のりを調べたとき、経路が分かっても、実際の交差点でどの方向に曲がればよいのか、何を目印に進めばよいのかが分からないことありませんか？特に、初めて訪れる場所では、地図と実際の風景を見比べながら進む必要があり、道に迷う不安があると思います。実際、私も初めて大学に行くときに道に迷ってしまい、遅刻しそうになる時がありました。

また、イベント主催者が参加者を会場まで案内するには、看板を設置したり、道中にスタッフを配置したりする必要があり、準備に手間や人員がかかります。Google Mapsなどの地図リンクを共有するだけでは、こうした不安を十分に解消できない場合もあります。

### 製品説明（具体的な製品の説明）
そこで私たちは、実際の写真を用いて目的地までの道のりを直感的に案内する、道案内アプリwayfinderを開発しました。道案内を作成する人は、出発地と目的地を入力し、道に迷いやすい交差点や分岐点など、案内に必要な地点をスマートフォンで撮影します。撮影した写真と位置情報をもとに経路を自動計算し、各地点の写真・目印・進行方向を組み合わせた、写真を順番にたどる道案内を生成できます。生成した道案内はURLやQRコードで共有できます。参加者は専用アプリのインストールや複雑な操作を必要とせず、共有されたURLを開くだけで利用できます。画面には、次に進むべき方向や目印となる風景写真が順番に表示され、参加者は実際の風景と見比べながら目的地まで移動できます。

### 特長
#### 1. 一度歩くだけで道案内を作成できる
作成者は、出発地から目的地までの道のりのうち、わかりにくい交差点や分岐点などをアプリ内で撮影するだけです。撮影した写真と位置情報を基に経路を計算し、それ以外の地点はGoogle Street Viewなどの画像データを活用します。これにより、道案内の作成にかかる手間を省きます。

#### 2. VLM が目印を自動抽出
各地点の画像を VLM (視覚言語モデル)で解析し、建物や看板などの目印と、進む方向や曲がる方向を自動で抽出します。さらに、「この看板を目印に右へ曲がるといった」の短い案内文を生成し、写真上に矢印を表示することで、視覚的にわかりやすい道案内を生成します。

#### 3. インストール不要ですぐに利用可能
Web アプリ（PWA）として提供し、参加者は共有されたURLを開くだけで利用できます。端末の位置情報を活用し、現在地に応じて次の案内への到達や通過・経路からの逸脱を判定することで、参加者が迷わず移動できるようにサポートします。

### 解決出来ること
作成者側： 看板の設置や案内スタッフの配置に頼らず、写真を撮影するだけで、直感的で分かりやすい道案内を短時間で作成できる
参加者側： 複雑な地図を読み解く必要がなく、画面に表示される写真と実際の風景を照らし合わせながら、次に進む方向を直感的に判断できる
運営全体： 道案内の作成・共有・利用を簡略化し、イベント会場への誘導にかかる準備や人員の負担を軽減できる

### 今後の展望
- 作成済み道案内のキャッシュ・流用（人気の会場・駅ペアの再利用）
- 迷いやすい地点の統計収集と、道案内の自動改善
- 作成者による目印文章の手動編集

### 注力したこと（こだわり等）
* 作る人・参加者ともに「操作をどれだけ省略できるか」を最優先に設計した
* 参加者側の位置判定はすべて端末内で完結させ、歩行中の通信状況に依存しない構成にした

## 開発技術
### 活用した技術
#### API・データ
* Google Routes API（経由地を含む徒歩経路計算）
* Google Geocoding API（出発地・目的地の座標変換）
* Google Street View Static API / Metadata API（交差点画像の取得）
* Gemini API / Claude API（画像入力による目印抽出。既定は Gemini、設定で Claude に切り替え可能）
* 国土地理院 地理院タイル（経路と地点の確認用地図）

#### フレームワーク・ライブラリ・モジュール
* フロントエンド: Vite, React, TypeScript, React Router, Tailwind CSS, jsQR
* バックエンド: FastAPI, uvicorn, Pydantic, httpx, Pillow, polyline, segno, zxing-cpp
* 地図表示: Leaflet
* DB・ストレージ: Supabase（Postgres + Storage）
* テスト・品質: Vitest, oxlint, pytest
* 開発時の公開: Cloudflare Tunnel

#### デバイス
* スマートフォン（iPhone / Android のブラウザ）
  * カメラ撮影は `<input capture>`、QR 読み取りは getUserMedia
  * 位置情報は Geolocation API
  * 写真への描き込みは Canvas API

### 独自技術
#### ハッカソンで開発した独自機能・技術
* 作成者の撮影地点を必ず経由する経路計算と、Street View による未撮影地点の自動補完
* VLM による目印抽出と、経路の方位差から算出した矢印の画像への描画
* 詳細は [docs/overview.md](./docs/overview.md)、[docs/creator.md](./docs/creator.md)、[docs/follower.md](./docs/follower.md) を参照

## ディレクトリ構成

```
hs_2601/
├── frontend/   # Web フロントエンド（Vite + React + TypeScript、PWA）
├── backend/    # API サーバー（FastAPI / Python）
└── docs/       # 企画・仕様・設計資料
```

- 全体像: [docs/overview.md](docs/overview.md)
- 作る人側: [docs/creator.md](docs/creator.md)
- 参加者側: [docs/follower.md](docs/follower.md)
- 詳細なディレクトリ構成と各ファイルの関係: [docs/directory-structure.md](docs/directory-structure.md)

機能は段階的に追加する。各ディレクトリ内の README.md に役割を記載する。

## 起動と画面確認

スマホの実機で、作る人・参加者の両方の画面が動くところまでの手順。
カメラ・位置情報・QR 読み取りは HTTPS が必要なので、Cloudflare Tunnel で開発 PC に一時的な `https://xxxx.trycloudflare.com` を付けて開く（無料、アカウント不要、WSL のポート転送設定も不要、同じ Wi-Fi でなくても開ける）。
詳しい説明とつまずきどころは [docs/tunnel.md](docs/tunnel.md)。

### 1. 初回のみ: 準備

```bash
cd frontend && npm install && cp .env.example .env.local && cd ..
cd backend && python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt && cd ..
```

- `backend/.env` に API キーと Supabase の接続情報を書く（`backend/.env.example` 参照）。
- `cloudflared` をインストールする（[docs/tunnel.md](docs/tunnel.md) の 1 章）。

### 2. バックエンドを起動して公開する

```bash
# ターミナル 1: API サーバー
cd backend && source .venv/bin/activate
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

```bash
# ターミナル 2: API サーバーに公開 URL を付ける
cloudflared tunnel --url http://localhost:8000
```

ログに出た `https://yyyy.trycloudflare.com` を控える。`https://yyyy.trycloudflare.com/health` を開いて `{"status":"ok"}` が出れば OK。

### 3. フロントを公開する

```bash
# ターミナル 3: フロントに公開 URL を付ける
cloudflared tunnel --url http://localhost:5173
```

ログに出た `https://xxxx.trycloudflare.com` を控える。

### 4. 公開 URL を設定に書く

```bash
# frontend/.env.local
VITE_API_MODE=server
VITE_API_BASE_URL=https://yyyy.trycloudflare.com   # 2 で控えた URL

# backend/.env
PUBLIC_BASE_URL=https://xxxx.trycloudflare.com     # 3 で控えた URL。参加者 URL と QR の飛び先になる
```

`backend/.env` を変えたら、ターミナル 1 の uvicorn を起動し直す。

### 5. フロントを起動する

```bash
# ターミナル 4
cd frontend && npm run dev
```

### 6. スマホで開く

| 画面 | 開く URL | できること |
|---|---|---|
| 作る人 | `https://xxxx.trycloudflare.com/c` | 出発地・目的地の入力、撮影、作成、一覧、公開 |
| 参加者の入口 | `https://xxxx.trycloudflare.com/r` | QR 読み取り、案内 ID の入力 |
| 参加者の道案内 | `https://xxxx.trycloudflare.com/r/7298a7dd6554` | 公開済みサンプル（命名「四天王寺→てんしば」）の写真列 |

作る人の画面で公開すると、その道の参加者 URL が出る。それを QR にしてスマホの標準カメラか参加者の入口で読めば、道案内が開く。

### 注意

- `cloudflared` を起動し直すと URL が変わる。そのたびに 4 と 5 をやり直し、配布済みの QR も作り直す。
- バックエンドなしで画面だけ見るときは、`frontend/.env.local` を `VITE_API_MODE=fixture` にして 3・5・6 だけ行う。写真列は `frontend/src/shared/fixtures/sampleRoutePlan.json` が表示される。
- 同じ Wi-Fi なら `npm run dev` の出力にある `Network:` の URL でも画面は見られるが、HTTPS ではないのでカメラ・位置情報・QR 読み取りは動かない。
- API の一覧はバックエンドの公開 URL の `/docs`（Swagger UI）で見られる。

# 会場までの道案内 作成アプリ（仮）

[![IMAGE ALT TEXT HERE](https://jphacks.com/wp-content/uploads/2026/07/IMG_5316.png)](https://www.youtube.com/watch?v=piaNsc6ilBI)

## 製品概要
### 背景(製品開発のきっかけ、課題等）
- イベント会場への道案内は、看板を立てたり途中に人を配置したりと、作る側の手間が大きい
- 一方で Google Map のリンクを渡すだけでは、交差点ごとの「何を目印にどちらへ曲がるか」が伝わらない
- 参加者が欲しいのは「駅から会場まで」の最低限の案内であり、地図アプリの付随情報は不要

### 製品説明（具体的な製品の説明）
- 作る人は出発地・目的地を入力し、分かりにくい地点だけをスマホで撮影する。写真と位置情報から経路を自動計算し、各曲がり角の写真・目印・進む方向をまとめた「写真列」の道案内を生成する
- 生成した道案内は URL・QR コードで公開できる
- 参加者は URL を開くだけで、現在地に応じて「次はこの写真の場所で右」といった案内を順に見ながら歩ける

### 特長
#### 1. 一度歩くだけで道案内ができる
分かりにくい地点をアプリ内で撮影するだけで、残りの交差点は Street View から自動補完し、経路・方向・距離をバックエンドが計算する

#### 2. VLM が目印を自動抽出
各地点の画像を VLM に入力し、「何を目印に、どちらへ曲がるか」の短い文章を自動生成する。曲がる方向は矢印として写真に描き込む

#### 3. 参加者側はインストール不要
Web アプリ（PWA）として動作し、URL を開くだけで利用できる。現在地から到達・通り過ぎ・経路外れを端末内で判定する

### 解決出来ること
- 作る側: 看板設置や人員配置なしに、写真ベースの直感的な道案内を短時間で用意できる
- 参加者側: 地図を読む必要がなく、目の前の風景と写真を照らし合わせるだけで会場に着ける

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
* Claude API（画像入力による目印抽出）

#### フレームワーク・ライブラリ・モジュール
* フロントエンド: Vite, React, TypeScript, vite-plugin-pwa, turf.js, idb-keyval, qrcode.react
* バックエンド: FastAPI, Pillow, httpx, polyline, geopy
* DB・ストレージ: Supabase（Postgres + Storage）
* ホスティング: Vercel / Cloudflare Pages

#### デバイス
* スマートフォン（iPhone / Android のブラウザ）。カメラは `<input capture>`、位置情報は Geolocation API を利用

### 独自技術
#### ハッカソンで開発した独自機能・技術
* 作成者の撮影地点を必ず経由する経路計算と、Street View による未撮影地点の自動補完
* VLM による目印抽出と、経路の方位差から算出した矢印の画像への描画
* 端末内で完結する到達・通り過ぎ・経路外れの判定ロジック
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

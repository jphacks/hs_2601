# 経路探索（route exploration）の中間形式と進捗計画

作る人側パイプラインの前半（ジオコーディング → 経路計算 → 曲がり角抽出 → Street View 取得）を
独立したコマンドとして実装する。その出力を後続の VLM・矢印描画が読む。

関連: [overview.md](./overview.md) 5 章、[creator.md](./creator.md) バックエンド節、
[directory-structure.md](./directory-structure.md)

## 1. 実行イメージ

```bash
cd backend
python -m scripts.explore_route "大阪駅" "グランフロント大阪" --out ./out
```

```
out/
├── route.json          # 中間形式（この文書の契約）
├── map.html            # 確認用の地図（Leaflet + OpenStreetMap、キー不要）。ピンと経路線、JSON を表示
├── raw/
│   ├── geocode.json    # Geocoding API の生レスポンス（デバッグ・fixture 用）
│   └── routes.json     # Routes API の生レスポンス
└── images/
    ├── 001.jpg
    └── 002.jpg
```

## 2. 中間形式 `route.json`

バックエンド内部でのみ使う。フロントには渡さないので、キーは Python 流の snake_case。
実装上の正は `backend/app/schemas/exploration.py`。この文書とスキーマがずれたらスキーマを優先する。

```json
{
  "version": 1,
  "origin":      { "query": "大阪駅",           "lat": 34.7025, "lng": 135.4959 },
  "destination": { "query": "グランフロント大阪", "lat": 34.7049, "lng": 135.4950 },
  "polyline": "encoded polyline (Google polyline5)",
  "total_distance_m": 480,
  "points": [
    {
      "index": 0,
      "lat": 34.7025,
      "lng": 135.4959,
      "heading": 85.0,
      "maneuver": "DEPART",
      "turn": "straight",
      "instruction": "北東に進む",
      "distance_to_next_m": 120,
      "image": "images/001.jpg",
      "image_source": "street_view",
      "street_view": { "pano_id": "abc", "date": "2023-05", "heading": 85.0, "fov": 90, "pitch": 0 },
      "landmark": null,
      "arrow_image": null
    }
  ]
}
```

### フィールド定義

| キー | 型 | 意味 |
|---|---|---|
| `version` | int | 形式のバージョン。破壊的変更時に上げる。現在 1 |
| `origin` / `destination` | object | 入力文字列 `query` と、ジオコーディング結果 `lat` `lng` |
| `polyline` | string | 経路全体のエンコード済みポリライン。参加者側の経路外れ判定にそのまま渡す |
| `total_distance_m` | int | 経路全長（m） |
| `points[]` | array | 曲がり角の配列。経路順。最後の要素は目的地 |

`points[]` の各要素:

| キー | 型 | 意味 | 決める人 |
|---|---|---|---|
| `index` | int | 0 始まりの連番 | turns |
| `lat` / `lng` | float | 曲がり角の座標 | turns |
| `heading` | float \| null | この地点から次の地点へ向かう方位（0〜360、北 = 0、時計回り）。最後の要素は null | turns |
| `maneuver` | string | Routes API の maneuver をそのまま（`TURN_LEFT`、`TURN_RIGHT`、`STRAIGHT`、`DEPART`、`ARRIVE` など） | turns |
| `turn` | `"left"` \| `"right"` \| `"straight"` \| `"arrive"` | maneuver を 4 種に正規化したもの。矢印描画と参加者表示が使う | turns |
| `instruction` | string | Routes API の案内文（日本語）。VLM が使えないときのフォールバック文に使う | turns |
| `distance_to_next_m` | int | 次の要素までの距離（m）。最後の要素は 0 | turns |
| `image` | string \| null | `out/` からの相対パス。Street View がない地点は null | streetview |
| `image_source` | `"street_view"` \| `"creator_photo"` \| null | 画像の出所。作成者の写真を差し込む段階で `creator_photo` が増える | streetview |
| `street_view` | object \| null | 取得時のパラメータ（pano_id、撮影年月、heading、fov、pitch）。再取得やデバッグ用 | streetview |
| `landmark` | string \| null | **後続の VLM ステップが埋める。** 探索段階では null | landmark |
| `arrow_image` | string \| null | **後続の矢印描画ステップが埋める。** 矢印を重ねた画像の相対パス | arrow |

### 決めごと

- `turn` の変換表: `TURN_LEFT` `TURN_SLIGHT_LEFT` `TURN_SHARP_LEFT` `UTURN_LEFT` → `left`、右も同様、`ARRIVE` → `arrive`、それ以外 → `straight`。
- `heading` は Routes API のステップのポリラインを使い、その地点から次の点への方位を計算する。Street View 取得時の `heading` にもこれを渡す。
- Street View は Metadata API で存在確認してから Static API を叩く。`status` が `OK` 以外なら `image` と `street_view` を null にする。
- 画像サイズは 640×640、`fov` 90、`pitch` 0 を既定値にする。
- 後続ステップは `route.json` を読み、`landmark` と `arrow_image` を埋めて同じ場所に上書き保存する。1 つのファイルがパイプラインを流れる。
- 写真列 JSON（フロントに渡す最終形）への変換は assemble ステップで行う。この中間形式を直接フロントに返さない。

## 3. 進捗計画

目標は「出発地・目的地を入れると、交差点ごとの Street View 画像と曲がる方向が並ぶ」。
各ステップは 1 ファイルで完結し、前のステップの出力だけに依存する。

| # | 作るもの | 完了の確認方法 | 依存 |
|---|---|---|---|
| 1 | `core/config.py`（`.env` から `GOOGLE_MAPS_API_KEY` を読む）、`schemas/exploration.py` | スキーマがこの文書の JSON を読み書きできる（完了） | なし |
| 2 | `external/google/geocoding.py` + `services/creator/geocode.py` + `services/creator/mapview.py` + `scripts/geocode.py` | `python -m scripts.geocode "大阪駅" "グランフロント大阪"` でピンが地図に出る（完了） | 1 |
| 3 | `external/google/routes.py` + `services/creator/route.py` + `scripts/route.py` | `python -m scripts.route "大阪駅" "グランフロント大阪"` で経路線とステップのピンが地図に出る（完了） | 2 |
| 4 | `services/creator/turns.py` | `raw/routes.json` だけから `points[]`（画像なし）が作れる。API キーなしでテスト可能 | 3 の fixture |
| 5 | `external/google/street_view.py` + `services/creator/streetview.py` | 各 point に `images/NNN.jpg` が付く。ない地点は null になる | 4 |
| 6 | `scripts/explore_route.py` | コマンド 1 発で `out/` 一式ができる | 2〜5 |
| 7 | （後続）`services/creator/landmark.py` | `landmark` が埋まる | 6、VLM キー |
| 8 | （後続）`services/creator/arrow.py` | `arrow_image` が埋まる | 6 |

- 4 は API キーが届く前でも着手できる。3 で取った生レスポンスを `tests/fixtures/routes_sample.json` として置く。
- 6 まで終われば中間発表のデモ素材になる。7 と 8 は並行で進められる。

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
| `heading` | float \| null | **交差点に近づく向き**（0〜360、北 = 0、時計回り）。参加者が見る向きに合わせる。出発点だけは出て行く向き | turns |
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
- `heading` は経路ポリライン上で、その地点の 10 m 手前から地点を見た方位（近づく向き）。Street View 取得時の `heading` にもこれを渡し、曲がる方向は矢印で重ねる。
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
| 4 | `services/creator/turns.py` + `geo.py` + `scripts/turns.py` | `python -m scripts.turns --from-raw ./out` で採用・不採用が色分けされた地図と `route.json` が出る（実装済み。しきい値は検証中） | 3 の fixture |
| 5 | `external/google/street_view.py` + `services/creator/streetview.py` | 各 point に `images/NNN.jpg` が付く。ない地点は null になる | 4 |
| 6 | `scripts/explore_route.py` | コマンド 1 発で `out/` 一式ができる | 2〜5 |
| 7 | （後続）`services/creator/landmark.py` | `landmark` が埋まる | 6、VLM キー |
| 8 | （後続）`services/creator/arrow.py` | `arrow_image` が埋まる | 6 |

- 4 は API キーが届く前でも着手できる。3 で取った生レスポンスを `tests/fixtures/routes_sample.json` として置く。
- 6 まで終われば中間発表のデモ素材になる。7 と 8 は並行で進められる。

## 4. 曲がり角抽出のロジック（ステップ 4）

「迷う地点」= 交差点などの判断が必要な地点、と定義する。一本道のカーブは対象にしない。屋内は今回スコープ外。

### 候補の作り方
- **Routes API のステップ境界だけを候補にする。** Google は案内が必要な地点でだけステップを切るので、道なりのカーブはステップの途中に埋もれて候補にならない。
- 目的地（ARRIVE）と、作成者が写真を撮った地点も候補に加える。

### 判定（各候補について、経路順に）
1. 直前の採用点から 5 m 未満 → **不採用（too_close）**。同じ交差点の重複とみなし統合する。目的地と作成者写真は対象外。
2. maneuver が `TURN_*` / `UTURN_*` / `ROUNDABOUT_*` / `DEPART` / `STRAIGHT`、または目的地・作成者写真 → **採用**。
   `STRAIGHT` を採用するのは、Google が「直進」を出すのは大通りを横切るなど直進が自明でない交差点だけだから。
3. maneuver が `NAME_CHANGE` または空 → 方位差で判定。10 m 手前から入る方位と 10 m 先へ出る方位の差 Δθ が 20° 以上なら **採用**、未満なら **不採用（small_heading_change）**。

### turn の正規化
| 条件 | turn |
|---|---|
| maneuver に LEFT / RIGHT を含む | left / right（API を優先） |
| ARRIVE | arrive |
| Δθ ≥ 20° / ≤ -20° | right / left |
| それ以外 | straight |
| \|Δθ\| > 150°（U ターン） | 左右に丸める |

### しきい値（`turns.py` 冒頭の定数。実データで調整する）
| 定数 | 値 | 意味 |
|---|---|---|
| `MIN_TURN_DEG` | 20° | これ未満は道なり |
| `MERGE_DISTANCE_M` | 5 m | 重複統合 |
| `BEARING_WINDOW_M` | 10 m | 方位を測る窓 |

### 実経路 5 件で分かった検討事項

**方針（10/24 決定）: 見逃すより多めに採用する。** 以下はいずれも現状のまま採用側に倒し、参加者側の表示で問題が出たら見直す。
- **横断歩道のジグザグ**: 道を渡る指示が「右折→左折」の 2 ステップ（10〜20 m 間隔）で出る。1 つの「渡る」地点に統合するか。
- **公園内の疑わしい TURN**: maneuver は TURN なのに Δθ が ±5° 以内のケースがある（中之島公園）。geometry を優先して不採用にするか。
- **NAME_CHANGE で案内文が「直進」**: Δθ が 35° でも案内文は「交差点を直進」。案内文を優先して straight にするか。
- **目的地直前の近接点**: 左折から 12 m で到着、のような場合も両方残す。目的地の写真は「ここが入口」の最終確認になる。

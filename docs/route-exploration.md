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
| `heading_out` | float \| null | 交差点から出て行く向き。目的地は null | turns |
| `maneuver` | string | Routes API の maneuver をそのまま（`TURN_LEFT`、`TURN_RIGHT`、`STRAIGHT`、`DEPART`、`ARRIVE` など） | turns |
| `turn` | `"left"` \| `"right"` \| `"straight"` \| `"arrive"` | maneuver を 4 種に正規化したもの。矢印描画と参加者表示が使う | turns |
| `instruction` | string | Routes API の案内文（日本語）。VLM が使えないときのフォールバック文に使う | turns |
| `distance_to_next_m` | int | 次の要素までの距離（m）。最後の要素は 0 | turns |
| `image` | string \| null | 採用した画像の `out/` からの相対パス。Street View がない地点は null。候補があるときは `chosen_candidate` の画像 | streetview → landmark |
| `candidates[]` | array | 向き・位置の違う候補画像（`image`、`heading_mode`、`street_view`、`score`）。ステップ 7 の採点が `score` に入る | streetview / landmark |
| `chosen_candidate` | int \| null | VLM が選んだ候補の番号。未評価なら null（`image` は先頭候補の仮採用） | landmark |
| `image_source` | `"street_view"` \| `"creator_photo"` \| null | 画像の出所。作成者の写真を差し込む段階で `creator_photo` が増える | streetview |
| `street_view` | object \| null | 取得時のパラメータ（pano_id、撮影年月、heading、fov、pitch、copyright、offset_m）。copyright に Google を含めば公式撮影 | streetview |
| `landmark` | string \| null | VLM が選んだ画像での目印の短い説明。VLM 不可なら案内文と距離からのフォールバック文 | landmark |
| `arrow_image` | string \| null | 採用画像に曲線の矢印を重ねた画像の相対パス。経路は VLM の `arrow_path`、無ければ turn ごとの既定形 | arrow |

### 決めごと

- `turn` の変換表: `TURN_LEFT` `TURN_SLIGHT_LEFT` `TURN_SHARP_LEFT` `UTURN_LEFT` → `left`、右も同様、`ARRIVE` → `arrive`、それ以外 → `straight`。
- `heading` は経路ポリライン上で、その地点の 10 m 手前から地点を見た方位（近づく向き）。`heading_out` は地点から 10 m 先を見た方位。
- Street View のカメラは既定で **両者の中間（bisector）** を向く。進入方向だけを向くと画角 90° では曲がる先の道が枠外になるため。曲がる方向は矢印で重ねる。
- Street View は Metadata API で存在確認してから Static API を叩く。`status` が `OK` 以外なら `image` と `street_view` を null にする。
- **Google 公式撮影のパノラマを優先する。** 最寄りがユーザー投稿なら 8 m ずつ手前に下がって最大 4 回探す（ユーザー投稿は夜景・屋内・船上が混ざる）。公式が無ければ最初の候補を使う。
- 既知の限界: 公式撮影にも船上（道頓堀の川）やトレッカー撮影が含まれ、道路上とは限らない。
- 既知の限界: 経路が建物内を通る区間（駅前ビルの通路など）では店舗内のパノラマが返る。撮影位置は経路から数 m なので距離では除外できない。屋内はスコープ外とし、必要になれば VLM に「屋内の画像か」を判定させてフォールバック文に回す。
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
| 5 | `external/google/street_view.py` + `services/creator/streetview.py` + `contact.py` + `scripts/streetview.py` | `python -m scripts.streetview --from-route DIR` で各地点に **候補画像が複数**（向き 3 種 × 位置 2 種、重複除去）並ぶ（完了） | 4 |
| 6 | `scripts/explore_route.py` + `services/creator/cache.py` | コマンド 1 発で `out/` 一式ができる。同じ入力は `.cache/` を再利用。7 も組み込み済み（完了） | 2〜5、7 |
| 7 | `external/vlm/`（Gemini / Claude）+ `services/creator/landmark.py` + `scripts/landmark.py` | VLM が候補ごとに「目印のわかりやすさ」「曲がる場所のわかりやすさ」を 1〜5 で採点し、最良の 1 枚を `image` に採用、`landmark` に目印文（完了。既定は Gemini 2.5 Flash-Lite の無料枠） | 5、VLM キー |
| 8 | `imaging/arrow.py` + `services/creator/arrow.py` + `scripts/arrow.py` | VLM が返した画像内の経路（`arrow_path`）に沿って曲線の矢印を描き `arrow_image` に入れる（完了） | 7 |

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

## 5. 画像の選定（ステップ 5 + 7）

1 地点につき Street View を複数枚取り、VLM に採点させて 1 枚を選ぶ。

### 候補（ステップ 5）
1 地点 **8 枚** を目標に、次の順で試し、同じパノラマ・同じ向き・同じ画角の重複は捨てる。

曲がり角: bisector/0 m → approach/0 m → bisector/10 m 手前 → departure/10 m 先（曲がった先の道路に入った位置）→ departure/0 m → bisector/20 m 手前 → departure/20 m 先 → bisector/0 m/fov110 → …（手前 30 m、先 40 m まで）

同じ撮影地点（pano）からは **3 枚まで**。1 つの地点に枠を使い切ると、その地点が使えないと判定されたときに候補が残らないため。

出発点・目的地（向きの違いが無い）: 位置を 0〜80 m の範囲でずらし（出発点は前方、目的地は手前）、fov 110 も混ぜる。

### 採点（ステップ 7）
- 1 地点につき VLM を 1 回呼び、全候補を一度に渡す（画像 N 枚 + プロンプト）。
- プロンプトには同じ撮影地点の画像グループ（例「画像 0,1,4 / 画像 2,7」）を渡す。立てるか・進めるかは向きではなく撮影地点の性質なので、グループ内の 1 枚でも該当すればその撮影地点の候補を全部除外する。
- 返答は JSON 固定: 候補ごとの `on_walkway`（**撮影地点に歩行者が立てるか**。船上・水上・階段の途中・柵の内側・店内・車道中央は false）、`path_blocked`（**足元と進む先の路面の間に柵・手すり・段差・水面があり歩いて行けないか**。true は採用しない）、`here_score`（**現在地のわかりやすさ** 1〜5。今ここにいると確信できるか、目印を含む）、`arrow_score`（**矢印の引きやすさ** 1〜5。どこを曲がるのかがはっきり見えるか）、`landmark`（20 字以内の目印文）、`reason`、`arrow_path`（**現在地 → 今の道 → 通りたい道** の路面中心線に沿って等間隔に打った 6〜12 点。左上 (0,0)〜右下 (1,1)）、全体の `best_index`。
- 2 つの合計が高いものを優先し、同点なら `arrow_score` を優先する。

### 矢印（ステップ 8）
- 採用候補の `arrow_path` の点を **直線で順につなぎ**、turn 色の単色（左 橙 / 右 紫 / 直進 青 / 到着 赤）の線と矢じりを描く。縁取りなし、折れ目は丸める。
- 左折なのに終点が左側（x ≤ 0.3）に無い、右折なのに右側（x ≥ 0.7）に無い場合は、終点をその側へ寄せて必ず曲線にする。
- `arrow_path` が無い（VLM 不可）地点は turn ごとの既定形（足元から奥へ、左右は横へ抜ける）。
- プロンプトは `backend/app/external/vlm/prompts/evaluate.txt`。
- 画像の SHA-256 + プロンプト + モデル名でキャッシュする。同じ候補に対する再実行は無料。
- VLM が使えない・失敗した・候補が無い地点は、Routes API の案内文と距離からのフォールバック文にする。

### VLM の選択
- 既定は **Gemini 3.5 Flash**（Google AI Studio の無料枠、課金登録不要）。Flash-Lite は「階段の踊り場」「柵の内側」のような立てない地点の判定を誤ることがあり、Flash なら正しく除外できた。`.env` の `VLM_PROVIDER=claude` で Claude Haiku に切り替え可能。
- 無料枠の 1 分あたり上限を避けるため、呼び出し間隔を `VLM_MIN_INTERVAL_S`（既定 4 秒）空け、429（上限）と 503（混雑）は待って再試行する。

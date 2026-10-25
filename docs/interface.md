# 作る人（backend）と参加者（frontend）の契約

バックエンドとフロントエンドを独立に開発するための接点。接点はこの 3 点だけで、両側はこれを見て別々に進める。
**変えるときは両側を同時に変える**（型は backend/app/schemas/route_plan.py と frontend/src/shared/types/routePlan.ts）。

## 1. データの形: `RoutePlanRecord`

Supabase のテーブル `route_plans` の 1 行。参加者が使うのは `plan_json`（= `RoutePlan`）。

| 列 | 型 | 内容 |
|---|---|---|
| `id` | text | 公開 ID。命名の SHA-256 先頭 12 桁（3 章） |
| `name` | text（unique） | 作る人が付けた命名 |
| `status` | `draft` / `published` | 参加者に見えるのは `published` だけ |
| `origin`, `destination` | text | 出発地・目的地の地名 |
| `plan_json` | jsonb | 下記 `RoutePlan` |
| `created_at`, `updated_at` | timestamptz | 保存日時。上書きで `updated_at` が進む |

`RoutePlan`:

```json
{
  "version": 1,
  "origin": "四天王寺 南大門",
  "destination": "天王寺公園 てんしば",
  "polyline": "cdorEeaczXx@C@GVLhGI…",
  "total_distance_m": 1012,
  "steps": [
    {
      "index": 0,
      "lat": 34.65298,
      "lng": 135.51651,
      "turn": "straight",
      "instruction": "直進して奈良街道/国道25号に向かう",
      "landmark": "天王寺南門筋の標識",
      "distance_to_next_m": 36,
      "image_url": "https://<project>.supabase.co/storage/v1/object/public/plans/7298a7dd6554/000.png"
    }
  ]
}
```

| フィールド | 型 | 内容 |
|---|---|---|
| `steps[].index` | int | 0 始まりの通し番号。経路順 |
| `steps[].lat`, `lng` | float | 地点の座標 |
| `steps[].turn` | `left` / `right` / `straight` / `arrive` | 曲がる方向。最後の地点は `arrive` |
| `steps[].instruction` | string | Routes API の案内文（改行を含むことがある） |
| `steps[].landmark` | string / null | VLM が作った目印の短い文 |
| `steps[].distance_to_next_m` | int | 次の地点までの距離。最後は 0 |
| `steps[].image_url` | string / null | 矢印入り画像の公開 URL。画像が無い地点は null |
| `polyline` | string | 経路全体の Google encoded polyline |
| `total_distance_m` | int | 経路全長 |

実物: `frontend/src/shared/fixtures/sampleRoutePlan.json`（バックエンドが実際に保存した `plan_json`）。
バックエンドは `backend/out/<dir>/published.json` に行全体の控えを出す。

## 2. 取り方: Supabase を直接読む

参加者側はバックエンドを経由せず、Supabase の REST を anon キーで読む。

```
GET {SUPABASE_URL}/rest/v1/route_plans?id=eq.<id>
    apikey: <SUPABASE_ANON_KEY>
```

- 返りは配列。先頭の 1 件を使う。空配列なら「未保存か未公開」。
- RLS により anon キーでは `status = 'published'` の行しか返らない。書き込みはできない。
- 名前で引くなら `?name=eq.<名前>`（URL エンコードする）。
- 画像 `image_url` は認証なしで `<img src>` に入れられる（公開バケット）。
- `SUPABASE_URL` と anon キーは `backend/.env` の `SUPABASE_URL` / `SUPABASE_ANON_KEY` と同じ値をフロントの環境変数に置く。anon キーは公開して良い（service_role キーはフロントに置かない）。

## 3. URL と ID

- 参加者画面の URL は `{PUBLIC_BASE_URL}/r/<id>`。`PUBLIC_BASE_URL` はフロントをデプロイした先（例 `https://xxx.vercel.app`）。
- `<id>` は命名を `strip()` した UTF-8 の SHA-256 を 16 進にした先頭 12 文字。同じ命名なら同じ ID で、保存し直すと上書きされる。
  ```python
  hashlib.sha256(name.strip().encode("utf-8")).hexdigest()[:12]
  ```
- QR コードはこの URL をそのまま符号化したもの。バックエンドが保存時に `qr.png` を出す（`scripts.publish`、`scripts.explore_route --name`）。
  フロントの公開完了画面で出す場合も同じ URL を QR にする。
- ID の文字は英数字・`-`・`_` のみ。

## 4. 作成入力: `PlanInput`（`photos.json`）

作る人が撮った写真列と出発地・目的地・命名をまとめた中間データ。バックエンドはこれだけを入口にする。
フロントから送る場合も、CLI で作る場合も同じ形。型は backend/app/schemas/creator_input.py（TypeScript 側は後で 1:1 に合わせる）。

```json
{
  "version": 1,
  "name": "四天王寺→てんしば",
  "origin": "四天王寺 南大門",
  "destination": { "query": "現在地", "lat": 34.6485, "lng": 135.5110 },
  "creator_id": "c_3f9a…",
  "created_at": "2026-10-25T10:12:00+09:00",
  "photos": [
    { "id": "9b1c", "seq": 0, "image": "photos/9b1c.jpg", "lat": 34.65268, "lng": 135.51657,
      "accuracy_m": 8, "taken_at": "2026-10-25T10:05:31+09:00", "location_source": "gps", "caption": null }
  ],
  "options": { "use_vlm_on_photos": false }
}
```

| フィールド | 必須 | 内容 |
|---|---|---|
| `name` | ○ | 命名。保存キー（ID はこのハッシュ） |
| `origin`, `destination` | ○ | 地名の文字列、または `{query, lat, lng}`（現在地から、など） |
| `creator_id` | 任意 | localStorage のランダム ID。一覧の絞り込み用 |
| `photos[].id` | ○ | フロントの `crypto.randomUUID()` など。英数字・`-`・`_` |
| `photos[].seq` | ○ | 撮影順。0 から連続で配列順と一致。経路はこの順に通る（順序の最適化はしない） |
| `photos[].image` | ○ | `photos/<id>.jpg`。入力ディレクトリからの相対パス |
| `photos[].lat`, `lng` | ○ | 撮影時の座標。無い写真は送れない（フロントで撮り直すか外す） |
| `photos[].accuracy_m` | 任意 | Geolocation の `accuracy`。道路への吸着が大きくずれた時の警告に使う |
| `photos[].taken_at` | 任意 | 撮影時刻（ISO 8601） |
| `photos[].location_source` | 任意 | `gps` / `manual` / `exif`。既定 `gps` |
| `photos[].caption` | 任意 | 作成者の一言。あれば目印文にそのまま使う |
| `options.use_vlm_on_photos` | 任意 | 既定 false。写真地点では Street View 取得・VLM・矢印を行わず、写真をそのまま使う |

- 画像の受け渡し（HTTP の場合）: `multipart/form-data` で `manifest`（上の JSON 文字列）と `photos`（ファイル）。
  ファイル名は `<id>.jpg` に付け替えて送り、バックエンドは `photos[].image` と突き合わせる。
- バックエンドは受信時に EXIF の回転を適用し長辺 1280px に縮小して `photos/<id>.jpg` に置き、`manifest` を `photos.json` として保存する。
  以降の処理はこのディレクトリだけを見る。HEIC など開けない形式は受け付けない。
- 経路は「出発地 → 写真 1 → … → 写真 n → 目的地」を区間ごとに計算して結合する。写真地点は `image_source = "creator_photo"` として写真列に入り、矢印は描かれない。

## 確認の仕方

- バックエンドだけ: `python -m scripts.show_plan --name "<命名>" --html ./out/plan.html`（anon キーで 2 章どおりに読み、画像を並べた HTML を出す）。
- フロントだけ: `sampleRoutePlan.json` を読む形で画面を作り、取得部分（`src/shared/api/serverApi.ts` の `getPublicRoute`）だけを 2 章の REST に差し替える。

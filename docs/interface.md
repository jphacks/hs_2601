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
      "image_url": "https://<project>.supabase.co/storage/v1/object/public/plans/7298a7dd6554/000.jpg"
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

## 確認の仕方

- バックエンドだけ: `python -m scripts.show_plan --name "<命名>" --html ./out/plan.html`（anon キーで 2 章どおりに読み、画像を並べた HTML を出す）。
- フロントだけ: `sampleRoutePlan.json` を読む形で画面を作り、取得部分（`src/shared/api/serverApi.ts` の `getPublicRoute`）だけを 2 章の REST に差し替える。

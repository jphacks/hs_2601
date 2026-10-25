# annotate — 写真への書き込みとメッセージ

撮った写真に **赤ペン / 青ペン / 消しゴム** で書き込み（任意）、**メッセージ**（任意・60 文字まで）を添える全画面の編集画面。
結果はバックエンドに依存しない形で返す。

- `blob`: 描画を焼き込んだ JPEG（長辺 1280px 以下・品質 0.88、EXIF の向きは適用済み）。描画が無くても JPEG 化して返す
- `caption`: 改行を空白にまとめ前後の空白を除いたメッセージ。空なら `null`
- `drawn`: ペンで何か描いたか

## 仕組み

- 写真キャンバスと線キャンバスを重ねる。線は「書き出し画像のピクセル座標」のストローク列で持ち、表示は CSS で縮小するだけ（書き出し後も位置がずれない）
- 消しゴムは線キャンバスに `destination-out` で描くストローク。写真は別レイヤーなので消えない。「戻す」で消しゴムの操作も 1 本ずつ戻せる
- 書き出し時は別キャンバスに線を描き直して写真に重ね、`toBlob('image/jpeg')`
- ペン幅は画像の長辺に比例（長辺 1280px で 13px）。消しゴムはその 4 倍

## ファイル

| ファイル | 内容 |
|---|---|
| `index.ts` | 公開窓口（`PhotoAnnotator`, `AnnotationResult`, `PhotoAnnotatorProps`） |
| `PhotoAnnotator.tsx` | 全画面の編集画面 |
| `DrawingSurface.tsx` | キャンバス 2 枚と Pointer Events |
| `AnnotatorToolbar.tsx` / `CaptionField.tsx` | 道具ボタン / メッセージ欄 |
| `strokes.ts` | ストロークのモデル・座標変換・サイズ計算（純粋関数・テストあり） |
| `caption.ts` | メッセージの文字数と正規化（純粋関数・テストあり） |
| `annotationState.ts` / `useAnnotation.ts` | 道具・線・メッセージの reducer（テストあり）と hook |
| `exportImage.ts` / `useLoadedImage.ts` | 画像の読み込み・描画・JPEG 書き出し（Canvas 依存、テストなし） |
| `preview.html` / `preview.tsx` / `PreviewApp.tsx` | 開発用プレビュー |

## 使い方

```tsx
import { PhotoAnnotator, type AnnotationResult } from '../annotate'

{editing && (
  <PhotoAnnotator
    source={editing.file}              // 元の File（再編集でも元の写真を渡す）
    initialCaption={editing.caption}   // 既存のメッセージ
    onDone={(r: AnnotationResult) => { saveAnnotation(editing.id, r); close() }}
    onCancel={close}
  />
)}
```

## 組み込み手順（撮影フロー）

1. 開く場所: 撮影直後（`addPhotos` の後に最後の 1 枚で開く）か、`PhotoGrid` のサムネイルをタップしたとき。
   全画面（`fixed inset-0 z-50`）で出るのでルーティングは不要
2. 保存する状態: `CapturedPhoto` に元の `file` は残したまま、`annotated?: Blob` と `caption?: string | null` を足す。
   `onDone` で `annotated = r.blob`、`caption = r.caption` を入れ、サムネイル（`preview`）は `annotated` の Object URL に差し替える（古い URL は revoke）
3. 再編集: `source` には元の `file` を、`initialCaption` には保存済みの `caption` を渡す（線は保持しないので描き直し）
4. 送信: `photos` に `annotated ?? file` を `<id>.jpg` として付け、manifest の `photos[].caption` に `caption` を入れる

## 開発用プレビュー

`npm run dev` の後、`http://localhost:5173/src/creator/annotate/preview.html` を開く（ルーターには載せていない・本番ビルドには入らない）。

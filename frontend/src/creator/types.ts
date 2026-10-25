/** 作る人（creator）画面だけで扱うデータ型。バックエンドと共有する型は shared/types に置く */

/** 撮影した写真 1 枚。File と撮影時の座標をペアで持つ */
export interface CapturedPhoto {
  /** crypto.randomUUID()。送信時のファイル名 `<id>.jpg` にもなる */
  id: string
  file: File
  /** サムネイル用の Object URL。削除時に revoke する */
  preview: string
  /** 撮影（取り込み）時刻。ISO 8601 */
  takenAt: string
  lat?: number
  lng?: number
  /** Geolocation の accuracy（m） */
  accuracyM?: number
  /** 位置情報が取れなかったときの理由 */
  locationError?: string
  /** 描画を焼き込んだ JPEG（annotate モジュールの出力）。あれば file の代わりに送る */
  annotated?: Blob
  /** 作成者のメッセージ。manifest の photos[].caption になり、その地点の目印文に使われる */
  caption?: string | null
}

/** 写真 1 枚の位置情報の状態 */
export type PhotoLocationStatus =
  | { kind: 'acquiring' }
  | { kind: 'ok'; lat: number; lng: number; accuracyM?: number }
  | { kind: 'failed'; reason: string }

/** 作る人（creator）画面だけで扱うデータ型。バックエンドと共有する型は shared/types に置く */

/** 撮影した写真 1 枚。File と撮影時の座標をペアで持つ */
export interface CapturedPhoto {
  id: string
  file: File
  /** サムネイル用の Object URL。削除時に revoke する */
  preview: string
  lat?: number
  lng?: number
  /** 位置情報が取れなかったときの理由 */
  locationError?: string
}

/** 写真注釈モジュールの公開型 */

export interface AnnotationResult {
  /** 描画を焼き込んだ JPEG（描画が無ければ元画像を JPEG 化したもの） */
  blob: Blob
  /** メッセージ。空なら null */
  caption: string | null
  /** 何か描いたか */
  drawn: boolean
}

export interface PhotoAnnotatorProps {
  /** 元の写真（File / Blob） */
  source: Blob
  /** 既存のメッセージ（再編集用） */
  initialCaption?: string | null
  onDone: (result: AnnotationResult) => void
  onCancel: () => void
}

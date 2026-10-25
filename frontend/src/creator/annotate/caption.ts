/** メッセージ（写真の一言）の文字数と正規化。純粋関数 */

/** メッセージの最大文字数 */
export const MAX_CAPTION_LENGTH = 60

/** 文字数（絵文字などのサロゲートペアも 1 文字と数える） */
export function captionLength(text: string): number {
  return Array.from(text).length
}

/** 上限を超えているか */
export function isCaptionTooLong(text: string, max: number = MAX_CAPTION_LENGTH): boolean {
  return captionLength(text) > max
}

/**
 * 送信用に整える。改行は空白 1 つにまとめ、前後の空白を除く。
 * 空なら null、上限を超えた分は切り捨てる。
 */
export function normalizeCaption(
  text: string | null | undefined,
  max: number = MAX_CAPTION_LENGTH,
): string | null {
  if (!text) return null
  const singleLine = text.replace(/\s*[\r\n]+\s*/g, ' ').trim()
  if (singleLine === '') return null
  return Array.from(singleLine).slice(0, max).join('').trim()
}

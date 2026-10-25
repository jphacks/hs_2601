/** API の失敗を利用者向けの日本語にする */
import { ApiError } from './client'

/** 状態コードごとの既定の文（バックエンドの detail が無いとき） */
const STATUS_MESSAGE: Record<number, string> = {
  400: '送った内容に不備があります',
  404: '見つかりませんでした',
  409: 'この名前の道は別の人が作っています。別の名前にしてください',
}

function detailOf(body: unknown): string | null {
  if (typeof body !== 'object' || body === null) return null
  const detail = (body as { detail?: unknown }).detail
  return typeof detail === 'string' && detail.trim() !== '' ? detail : null
}

/**
 * FastAPI の `{"detail": "..."}` があればそれを、無ければ状態コードの既定文、どちらも無ければ fallback。
 * 409 はバックエンドの理由（公開中・別の人の名前・作成中）をそのまま出し、無ければ名前の付け直しを促す。
 */
export function apiErrorMessage(e: unknown, fallback: string): string {
  if (e instanceof ApiError) {
    return detailOf(e.body) ?? STATUS_MESSAGE[e.status] ?? fallback
  }
  if (e instanceof TypeError) return 'サーバーに接続できませんでした。通信状態を確認してください'
  return e instanceof Error ? e.message : fallback
}

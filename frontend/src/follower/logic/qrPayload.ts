/** QR コードの中身から道案内 ID を取り出す純関数 */

/** backend/app/schemas/route_plan.py の PLAN_ID_PATTERN と同じ */
const ROUTE_ID_PATTERN = /^[A-Za-z0-9_-]{1,64}$/
const ROUTE_PATH_PATTERN = /\/r\/([A-Za-z0-9_-]{1,64})\/?$/

/**
 * 受け付ける形:
 *  - ID そのもの（例: 7298a7dd6554）
 *  - 参加者 URL（例: https://example.com/r/7298a7dd6554）
 * どちらでもなければ null
 */
export function routeIdFromQr(text: string): string | null {
  const trimmed = text.trim()
  if (ROUTE_ID_PATTERN.test(trimmed)) return trimmed
  try {
    const match = new URL(trimmed).pathname.match(ROUTE_PATH_PATTERN)
    return match ? match[1] : null
  } catch {
    return null
  }
}

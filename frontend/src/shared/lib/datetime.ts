/** 日時の文字列変換 */

function pad(n: number): string {
  return String(Math.abs(n)).padStart(2, '0')
}

/**
 * 端末のタイムゾーンのオフセット付き ISO 8601（例 `2026-10-25T10:05:31+09:00`）。
 * interface.md 4 章の `taken_at` / `created_at` の書き方に合わせる。
 */
export function toIsoWithOffset(date: Date): string {
  const offsetMin = -date.getTimezoneOffset()
  const sign = offsetMin >= 0 ? '+' : '-'
  const ymd = `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}`
  const hms = `${pad(date.getHours())}:${pad(date.getMinutes())}:${pad(date.getSeconds())}`
  const offset = `${sign}${pad(Math.trunc(offsetMin / 60))}:${pad(offsetMin % 60)}`
  return `${ymd}T${hms}${offset}`
}

/** 一覧などに出す短い日付表示（例 `2026/10/25 10:05`）。読めなければ元の文字列 */
export function formatDateTime(iso: string): string {
  const date = new Date(iso)
  if (Number.isNaN(date.getTime())) return iso
  const ymd = `${date.getFullYear()}/${pad(date.getMonth() + 1)}/${pad(date.getDate())}`
  return `${ymd} ${pad(date.getHours())}:${pad(date.getMinutes())}`
}

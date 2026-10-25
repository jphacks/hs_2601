import { describe, expect, it } from 'vitest'
import { formatDateTime, toIsoWithOffset } from './datetime'

describe('toIsoWithOffset', () => {
  it('オフセット付き ISO 8601 で、元の時刻（秒単位）に戻せる', () => {
    const date = new Date('2026-10-25T01:05:31.789Z')
    const iso = toIsoWithOffset(date)
    expect(iso).toMatch(/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}[+-]\d{2}:\d{2}$/)
    expect(Date.parse(iso)).toBe(Date.parse('2026-10-25T01:05:31Z'))
  })
})

describe('formatDateTime', () => {
  it('年/月/日 時:分 にする', () => {
    expect(formatDateTime(toIsoWithOffset(new Date(2026, 9, 5, 9, 3)))).toBe('2026/10/05 09:03')
  })

  it('読めない文字列はそのまま返す', () => {
    expect(formatDateTime('not a date')).toBe('not a date')
  })
})

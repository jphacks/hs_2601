import { describe, expect, it } from 'vitest'
import { routeIdFromQr } from './qrPayload'

describe('routeIdFromQr', () => {
  it('ID そのものを受け付ける（前後の空白は無視）', () => {
    expect(routeIdFromQr('7298a7dd6554')).toBe('7298a7dd6554')
    expect(routeIdFromQr('  abc_-123 \n')).toBe('abc_-123')
  })

  it('参加者 URL から ID を取り出す', () => {
    expect(routeIdFromQr('https://example.com/r/7298a7dd6554')).toBe('7298a7dd6554')
    expect(routeIdFromQr('http://localhost:5173/r/7298a7dd6554/')).toBe('7298a7dd6554')
    expect(routeIdFromQr('https://example.com/r/abc?x=1#top')).toBe('abc')
  })

  it('道案内のものでなければ null', () => {
    expect(routeIdFromQr('')).toBeNull()
    expect(routeIdFromQr('https://example.com/')).toBeNull()
    expect(routeIdFromQr('https://example.com/c/routes/abc')).toBeNull()
    expect(routeIdFromQr('四天王寺→てんしば')).toBeNull()
    expect(routeIdFromQr('a'.repeat(65))).toBeNull()
  })
})

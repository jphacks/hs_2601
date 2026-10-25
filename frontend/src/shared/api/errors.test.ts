import { describe, expect, it } from 'vitest'
import { ApiError } from './client'
import { apiErrorMessage } from './errors'

describe('apiErrorMessage', () => {
  it('FastAPI の detail（文字列）があればそれを使う', () => {
    expect(apiErrorMessage(new ApiError(400, { detail: '写真の枚数が合いません' }), 'x')).toBe(
      '写真の枚数が合いません',
    )
  })

  it('409 は名前の付け直しを促す', () => {
    expect(apiErrorMessage(new ApiError(409, { detail: 'conflict' }), 'x')).toContain('別の名前')
  })

  it('detail が文字列でない（422 の配列など）なら状態コードの既定文か fallback', () => {
    expect(apiErrorMessage(new ApiError(400, { detail: [{ msg: 'x' }] }), 'fb')).toBe('送った内容に不備があります')
    expect(apiErrorMessage(new ApiError(422, { detail: [{ msg: 'x' }] }), 'fb')).toBe('fb')
    expect(apiErrorMessage(new ApiError(500, 'Internal Server Error'), 'fb')).toBe('fb')
  })

  it('fetch 自体の失敗（TypeError）は接続できない旨', () => {
    expect(apiErrorMessage(new TypeError('Failed to fetch'), 'fb')).toContain('接続できませんでした')
  })

  it('それ以外の Error は message、Error でなければ fallback', () => {
    expect(apiErrorMessage(new Error('変換失敗'), 'fb')).toBe('変換失敗')
    expect(apiErrorMessage('oops', 'fb')).toBe('fb')
  })
})

import { describe, expect, it } from 'vitest'
import { validateDraft } from './useCreateRoute'

const photo = {
  id: 'p1',
  file: new File(['x'], 'a.jpg', { type: 'image/jpeg' }),
  preview: 'blob:x',
}

describe('validateDraft', () => {
  it('出発地か目的地が空白だけならエラー', () => {
    expect(validateDraft({ origin: ' ', destination: 'B', photos: [photo] })).toBe(
      '出発地と目的地を入力してください',
    )
    expect(validateDraft({ origin: 'A', destination: '', photos: [photo] })).toBe(
      '出発地と目的地を入力してください',
    )
  })

  it('写真がなければエラー', () => {
    expect(validateDraft({ origin: 'A', destination: 'B', photos: [] })).toBe(
      '目印となる写真を撮影してください',
    )
  })

  it('揃っていれば null', () => {
    expect(validateDraft({ origin: 'A', destination: 'B', photos: [photo] })).toBeNull()
  })
})

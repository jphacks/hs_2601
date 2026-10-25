import { describe, expect, it } from 'vitest'
import type { CapturedPhoto } from '../types'
import { buildCreateInput, convertPhotos, validateDraft, type DraftInput } from './useCreateRoute'

function photo(id: string, extra: Partial<CapturedPhoto> = {}): CapturedPhoto {
  return {
    id,
    file: new File(['x'], `${id}.heic`, { type: 'image/heic' }),
    preview: 'blob:x',
    takenAt: '2026-10-25T10:05:31+09:00',
    lat: 34.6,
    lng: 135.5,
    accuracyM: 8,
    ...extra,
  }
}

function draft(overrides: Partial<DraftInput> = {}): DraftInput {
  return { name: '広島駅→平和記念公園', origin: 'A', destination: 'B', photos: [photo('p1')], ...overrides }
}

describe('validateDraft', () => {
  it('命名が空白だけならエラー', () => {
    expect(validateDraft(draft({ name: '  ' }))).toBe('道の名前を入力してください')
  })

  it('出発地か目的地が空白だけならエラー', () => {
    expect(validateDraft(draft({ origin: ' ' }))).toBe('出発地と目的地を入力してください')
    expect(validateDraft(draft({ destination: '' }))).toBe('出発地と目的地を入力してください')
  })

  it('写真がなければエラー', () => {
    expect(validateDraft(draft({ photos: [] }))).toBe('目印となる写真を撮影してください')
  })

  it('位置情報が取れなかった写真があれば、その番号を出してエラー', () => {
    const photos = [photo('p1'), photo('p2', { lat: undefined, lng: undefined, locationError: '拒否' })]
    expect(validateDraft(draft({ photos }))).toBe(
      '目印 2 の位置情報が取れていません。位置を取り直すか、写真を削除してください',
    )
  })

  it('位置情報を取得中の写真があればエラー', () => {
    const photos = [photo('p1', { lat: undefined, lng: undefined }), photo('p2'), photo('p3', { lat: undefined, lng: undefined })]
    expect(validateDraft(draft({ photos }))).toContain('目印 1・目印 3 の位置情報を取得中です')
  })

  it('揃っていれば null', () => {
    expect(validateDraft(draft())).toBeNull()
  })
})

describe('convertPhotos', () => {
  it('順番どおりに 1 枚ずつ変換する', async () => {
    const order: string[] = []
    const jpegs = await convertPhotos([photo('p1'), photo('p2')], async (file) => {
      order.push(file.name)
      return new Blob([file.name], { type: 'image/jpeg' })
    })
    expect(order).toEqual(['p1.heic', 'p2.heic'])
    expect(jpegs).toHaveLength(2)
  })

  it('開けない写真があれば、その番号を出して失敗する', async () => {
    const convert = async (file: File) => {
      if (file.name === 'p2.heic') throw new Error('decode failed')
      return new Blob(['ok'])
    }
    await expect(convertPhotos([photo('p1'), photo('p2')], convert)).rejects.toThrow('目印 2 の写真を読み込めませんでした')
  })
})

describe('buildCreateInput', () => {
  const jpeg = new Blob(['jpeg'], { type: 'image/jpeg' })

  it('命名などを trim し、写真に変換後の JPEG と座標・精度・撮影時刻を付ける', () => {
    const input = buildCreateInput(
      draft({ name: ' 命名 ', origin: ' A ', photos: [photo('p1')] }),
      [jpeg],
      'c1',
      '2026-10-25T10:12:00+09:00',
    )
    expect(input).toEqual({
      name: '命名',
      origin: 'A',
      destination: 'B',
      creatorId: 'c1',
      createdAt: '2026-10-25T10:12:00+09:00',
      photos: [
        { id: 'p1', file: jpeg, lat: 34.6, lng: 135.5, accuracyM: 8, takenAt: '2026-10-25T10:05:31+09:00' },
      ],
    })
  })

  it('座標が無い写真や枚数の不一致は例外', () => {
    const noLocation = draft({ photos: [photo('p1', { lat: undefined, lng: undefined })] })
    expect(() => buildCreateInput(noLocation, [jpeg], 'c1', 'x')).toThrow('目印 1 の位置情報がありません')
    expect(() => buildCreateInput(draft(), [], 'c1', 'x')).toThrow()
  })
})

import { describe, expect, it } from 'vitest'
import { geolocationErrorMessage, locationLabel, photoLocationStatus } from './photoLocation'
import type { CapturedPhoto } from './types'

const base: CapturedPhoto = {
  id: 'p1',
  file: new File(['x'], 'a.jpg', { type: 'image/jpeg' }),
  preview: 'blob:x',
  takenAt: '2026-10-25T10:05:31+09:00',
}

describe('photoLocationStatus', () => {
  it('座標があれば ok（精度付き）', () => {
    expect(photoLocationStatus({ ...base, lat: 1, lng: 2, accuracyM: 8.4 })).toEqual({
      kind: 'ok',
      lat: 1,
      lng: 2,
      accuracyM: 8.4,
    })
  })

  it('エラーがあれば failed、どちらも無ければ取得中', () => {
    expect(photoLocationStatus({ ...base, locationError: '拒否' })).toEqual({ kind: 'failed', reason: '拒否' })
    expect(photoLocationStatus(base)).toEqual({ kind: 'acquiring' })
  })
})

describe('locationLabel', () => {
  it('精度は m に丸めて ±N m で出す', () => {
    expect(locationLabel({ kind: 'ok', lat: 1, lng: 2, accuracyM: 8.4 })).toBe('位置情報 OK（±8m）')
    expect(locationLabel({ kind: 'ok', lat: 1, lng: 2 })).toBe('位置情報 OK')
  })

  it('失敗と取得中', () => {
    expect(locationLabel({ kind: 'failed', reason: '拒否' })).toBe('位置情報なし（拒否）')
    expect(locationLabel({ kind: 'acquiring' })).toBe('位置情報を取得中...')
  })
})

describe('geolocationErrorMessage', () => {
  it('コードごとの日本語、未知のコードは既定文', () => {
    expect(geolocationErrorMessage(1)).toContain('許可')
    expect(geolocationErrorMessage(3)).toContain('時間')
    expect(geolocationErrorMessage(99)).toBe('位置情報を取得できませんでした')
  })
})

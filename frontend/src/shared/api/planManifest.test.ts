import { describe, expect, it } from 'vitest'
import type { CreateRouteInput } from '../types/creator'
import { buildPlanManifest, photoFileName } from './planManifest'

const blob = new Blob(['x'], { type: 'image/jpeg' })

const input: CreateRouteInput = {
  name: ' 四天王寺→てんしば ',
  origin: '四天王寺 南大門',
  destination: '天王寺公園 てんしば',
  creatorId: 'c_1',
  createdAt: '2026-10-25T10:12:00+09:00',
  photos: [
    { id: 'a-1', file: blob, lat: 34.65268, lng: 135.51657, accuracyM: 8, takenAt: '2026-10-25T10:05:31+09:00' },
    { id: 'b_2', file: blob, lat: 34.651, lng: 135.515 },
  ],
}

describe('buildPlanManifest', () => {
  it('4 章の PlanInput（snake_case、seq は配列順、画像は photos/<id>.jpg）になる', () => {
    expect(buildPlanManifest(input, 'unused')).toEqual({
      version: 1,
      name: '四天王寺→てんしば',
      origin: '四天王寺 南大門',
      destination: '天王寺公園 てんしば',
      creator_id: 'c_1',
      created_at: '2026-10-25T10:12:00+09:00',
      photos: [
        {
          id: 'a-1',
          seq: 0,
          image: 'photos/a-1.jpg',
          lat: 34.65268,
          lng: 135.51657,
          accuracy_m: 8,
          taken_at: '2026-10-25T10:05:31+09:00',
          location_source: 'gps',
          caption: null,
        },
        {
          id: 'b_2',
          seq: 1,
          image: 'photos/b_2.jpg',
          lat: 34.651,
          lng: 135.515,
          accuracy_m: null,
          taken_at: null,
          location_source: 'gps',
          caption: null,
        },
      ],
      options: { use_vlm_on_photos: false },
    })
  })

  it('目的地が空白だけなら null（最後の写真がゴール）', () => {
    expect(buildPlanManifest({ ...input, destination: '  ' }, 'unused').destination).toBeNull()
  })

  it('写真のメッセージは photos[].caption に入る', () => {
    const withCaption = { ...input, photos: [{ ...input.photos[0], caption: '赤い看板を右へ' }] }
    expect(buildPlanManifest(withCaption, 'unused').photos[0].caption).toBe('赤い看板を右へ')
  })

  it('createdAt が無ければ fallback を使う。写真 0 枚も作れる', () => {
    const manifest = buildPlanManifest({ ...input, createdAt: undefined, photos: [] }, '2026-01-01T00:00:00+09:00')
    expect(manifest.created_at).toBe('2026-01-01T00:00:00+09:00')
    expect(manifest.photos).toEqual([])
  })

  it('JSON にしても File などが混ざらない', () => {
    const json = JSON.parse(JSON.stringify(buildPlanManifest(input, 'x')))
    expect(Object.keys(json.photos[0])).not.toContain('file')
  })

  it('写真 ID に使えない文字があれば例外', () => {
    const bad = { ...input, photos: [{ id: '../x', file: blob, lat: 0, lng: 0 }] }
    expect(() => buildPlanManifest(bad, 'x')).toThrow()
  })

  it('crypto.randomUUID() の ID は使える', () => {
    const id = crypto.randomUUID()
    const manifest = buildPlanManifest({ ...input, photos: [{ id, file: blob, lat: 0, lng: 0 }] }, 'x')
    expect(manifest.photos[0].image).toBe(`photos/${photoFileName(id)}`)
  })
})

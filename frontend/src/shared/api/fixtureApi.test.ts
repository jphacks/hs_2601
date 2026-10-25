import { describe, expect, it } from 'vitest'
import type { CreateRouteInput } from '../types/creator'
import { ApiError } from './client'
import { createFixtureApi, fixtureRouteId, SAMPLE_ROUTE_ID } from './fixtureApi'

const PHOTO = { id: 'p1', file: new Blob(['x'], { type: 'image/jpeg' }), lat: 34.6, lng: 135.5 }

function input(overrides: Partial<CreateRouteInput> = {}): CreateRouteInput {
  return { name: '広島駅→平和記念公園', origin: '広島駅', destination: '平和記念公園', photos: [PHOTO], creatorId: 'c1', ...overrides }
}

function apiWithClock(start = 0) {
  let t = start
  const api = createFixtureApi({ now: () => t, createDelayMs: 1000, publicOrigin: 'https://example.test' })
  return { api, advance: (ms: number) => (t += ms) }
}

describe('createFixtureApi', () => {
  it('最初からサンプルの道案内が 1 件、公開済みで入っている', async () => {
    const { api } = apiWithClock()
    const list = await api.listRoutes('anyone')
    expect(list).toHaveLength(1)
    expect(list[0]).toMatchObject({ id: SAMPLE_ROUTE_ID, name: '四天王寺→てんしば', status: 'published' })
    expect(Date.parse(list[0].createdAt)).not.toBeNaN()

    const record = await api.getPublicRoutePlan(SAMPLE_ROUTE_ID)
    expect(record.plan.steps.length).toBeGreaterThan(0)
    expect(record.plan.steps.at(-1)?.turn).toBe('arrive')
  })

  it('作成受付で命名から決まる routeId が返り、待ち時間中は step が進み、過ぎると下書きが増える', async () => {
    const { api, advance } = apiWithClock()
    const { jobId, routeId } = await api.createRoute(input())
    expect(routeId).toBe(fixtureRouteId('広島駅→平和記念公園'))

    expect(await api.getJobStatus(jobId)).toMatchObject({ state: 'running', step: 'geocode' })
    advance(600)
    expect(await api.getJobStatus(jobId)).toMatchObject({ state: 'running', step: 'landmark' })
    advance(400)
    const done = await api.getJobStatus(jobId)
    expect(done).toMatchObject({ state: 'done', routeId })

    const record = await api.getRoutePlan(routeId)
    expect(record).toMatchObject({ name: '広島駅→平和記念公園', status: 'draft', origin: '広島駅' })
    expect(record.plan.origin).toBe('広島駅')

    const list = await api.listRoutes('c1')
    expect(list).toHaveLength(2)
    expect(list.find((r) => r.id === routeId)).toMatchObject({ name: '広島駅→平和記念公園', status: 'draft' })
    // 完了後に問い合わせても done のまま
    expect((await api.getJobStatus(jobId)).state).toBe('done')
  })

  it('一覧は自分の作ったもの（と最初から入っている分）だけ', async () => {
    const { api, advance } = apiWithClock()
    const { jobId } = await api.createRoute(input())
    advance(1000)
    await api.getJobStatus(jobId)
    expect(await api.listRoutes('someone-else')).toHaveLength(1)
  })

  it('同じ命名は同じ作成者なら上書き、別の作成者なら 409', async () => {
    const { api, advance } = apiWithClock()
    const first = await api.createRoute(input())
    advance(1000)
    await api.getJobStatus(first.jobId)

    const again = await api.createRoute(input({ name: ' 広島駅→平和記念公園 ' }))
    expect(again.routeId).toBe(first.routeId)
    await expect(api.createRoute(input({ creatorId: 'c2' }))).rejects.toMatchObject({ status: 409 })
    await expect(api.createRoute(input({ name: '四天王寺→てんしば' }))).rejects.toMatchObject({ status: 409 })
  })

  it('命名が空なら 400', async () => {
    const { api } = apiWithClock()
    await expect(api.createRoute(input({ name: '  ' }))).rejects.toMatchObject({ status: 400 })
  })

  it('下書きは参加者向け取得で 404、公開すると取れるようになり URL が返る（QR は無し）', async () => {
    const { api, advance } = apiWithClock()
    const { jobId, routeId } = await api.createRoute(input({ name: 'A→B' }))
    advance(1000)
    await api.getJobStatus(jobId)

    await expect(api.getPublicRoutePlan(routeId)).rejects.toBeInstanceOf(ApiError)

    const result = await api.publishRoute(routeId)
    expect(result).toEqual({ routeId, url: `https://example.test/r/${routeId}`, qrPath: null })
    expect((await api.getPublicRoutePlan(routeId)).status).toBe('published')
  })

  it('存在しない ID は 404 の ApiError', async () => {
    const { api } = apiWithClock()
    await expect(api.getRoutePlan('nope')).rejects.toMatchObject({ status: 404 })
    await expect(api.getJobStatus('nope')).rejects.toMatchObject({ status: 404 })
  })
})

describe('fixtureRouteId', () => {
  it('前後の空白を無視して同じ命名なら同じ 12 桁の 16 進', () => {
    expect(fixtureRouteId(' あ ')).toBe(fixtureRouteId('あ'))
    expect(fixtureRouteId('あ')).toMatch(/^[0-9a-f]{12}$/)
    expect(fixtureRouteId('あ')).not.toBe(fixtureRouteId('い'))
  })
})

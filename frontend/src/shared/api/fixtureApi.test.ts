import { describe, expect, it } from 'vitest'
import { ApiError } from './client'
import { createFixtureApi, SAMPLE_ROUTE_ID } from './fixtureApi'

const PHOTO = { file: new File(['x'], 'a.jpg', { type: 'image/jpeg' }), lat: 34.6, lng: 135.5 }

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
    expect(list[0]).toMatchObject({ id: SAMPLE_ROUTE_ID, status: 'published' })

    const record = await api.getPublicRoutePlan(SAMPLE_ROUTE_ID)
    expect(record.plan.steps.length).toBeGreaterThan(0)
    expect(record.plan.steps.at(-1)?.turn).toBe('arrive')
  })

  it('作成受付 → 待ち時間が過ぎると完了し、下書きの道案内が増える', async () => {
    const { api, advance } = apiWithClock()
    const { jobId } = await api.createRoute({
      origin: '広島駅',
      destination: '平和記念公園',
      photos: [PHOTO],
      creatorId: 'c1',
    })

    expect(await api.getJobStatus(jobId)).toMatchObject({ state: 'running' })
    advance(1000)
    const done = await api.getJobStatus(jobId)
    expect(done.state).toBe('done')

    const record = await api.getRoutePlan(done.routeId!)
    expect(record).toMatchObject({ status: 'draft', origin: '広島駅', destination: '平和記念公園' })
    expect(record.plan.origin).toBe('広島駅')
    expect(await api.listRoutes('c1')).toHaveLength(2)
  })

  it('下書きは参加者向け取得で 404、公開すると取れるようになり URL が返る', async () => {
    const { api, advance } = apiWithClock()
    const { jobId } = await api.createRoute({ origin: 'A', destination: 'B', photos: [PHOTO], creatorId: 'c1' })
    advance(1000)
    const { routeId } = await api.getJobStatus(jobId)

    await expect(api.getPublicRoutePlan(routeId!)).rejects.toBeInstanceOf(ApiError)

    const result = await api.publishRoute(routeId!)
    expect(result.url).toBe(`https://example.test/r/${routeId}`)
    expect((await api.getPublicRoutePlan(routeId!)).status).toBe('published')
  })

  it('存在しない ID は 404 の ApiError', async () => {
    const { api } = apiWithClock()
    await expect(api.getRoutePlan('nope')).rejects.toMatchObject({ status: 404 })
    await expect(api.getJobStatus('nope')).rejects.toMatchObject({ status: 404 })
  })
})

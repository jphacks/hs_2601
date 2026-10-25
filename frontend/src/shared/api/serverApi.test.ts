import { afterEach, describe, expect, it, vi } from 'vitest'
import { serverApi } from './serverApi'

function stubFetch(status: number, body: unknown) {
  const fetchMock = vi.fn(async () => new Response(JSON.stringify(body), { status }))
  vi.stubGlobal('fetch', fetchMock)
  return fetchMock
}

function lastCall(fetchMock: ReturnType<typeof stubFetch>): [string, RequestInit] {
  return fetchMock.mock.calls.at(-1) as unknown as [string, RequestInit]
}

afterEach(() => {
  vi.unstubAllGlobals()
})

describe('serverApi', () => {
  it('作成受付は multipart で manifest（JSON 文字列）と photos（<id>.jpg）を送る', async () => {
    const fetchMock = stubFetch(202, { jobId: 'j1', routeId: 'r1' })
    const jpeg = new Blob(['jpeg'], { type: 'image/jpeg' })

    const result = await serverApi.createRoute({
      name: '命名',
      origin: 'A',
      destination: 'B',
      creatorId: 'c1',
      createdAt: '2026-10-25T10:12:00+09:00',
      photos: [
        { id: 'p1', file: jpeg, lat: 1, lng: 2, accuracyM: 5 },
        { id: 'p2', file: jpeg, lat: 3, lng: 4 },
      ],
    })

    expect(result).toEqual({ jobId: 'j1', routeId: 'r1' })
    const [url, init] = lastCall(fetchMock)
    expect(url).toMatch(/\/api\/routes$/)
    expect(init.method).toBe('POST')
    const form = init.body as FormData
    const manifest = JSON.parse(form.get('manifest') as string)
    expect(manifest).toMatchObject({ version: 1, name: '命名', creator_id: 'c1' })
    expect(manifest.photos.map((p: { image: string }) => p.image)).toEqual(['photos/p1.jpg', 'photos/p2.jpg'])
    const files = form.getAll('photos') as File[]
    expect(files.map((f) => f.name)).toEqual(['p1.jpg', 'p2.jpg'])
  })

  it('一覧は creator_id を付けて GET、公開は POST', async () => {
    const fetchMock = stubFetch(200, [])
    await serverApi.listRoutes('c 1')
    expect(lastCall(fetchMock)[0]).toMatch(/\/api\/routes\?creator_id=c%201$/)

    stubFetch(200, { routeId: 'r1', url: 'https://x/r/r1', qrPath: '/api/routes/r1/qr.png' })
    const published = await serverApi.publishRoute('r1')
    expect(published.qrPath).toBe('/api/routes/r1/qr.png')
  })

  it('409 は status と detail を持つ ApiError', async () => {
    stubFetch(409, { detail: '同じ命名の道があります' })
    await expect(serverApi.getJobStatus('j1')).rejects.toMatchObject({
      status: 409,
      body: { detail: '同じ命名の道があります' },
    })
  })
})

/**
 * バックエンドなしで画面を動かすための RouteApi 実装。
 * 写真列は shared/fixtures/sampleRoutePlan.json を返し、作成・公開はメモリ上の一覧だけを更新する。
 * 本物の API ができたら endpoints.ts の切り替えで serverApi.ts に差し替える。
 */
import samplePlanJson from '../fixtures/sampleRoutePlan.json'
import { FIXTURE_CREATE_DELAY_MS } from '../lib/constants'
import type { CreateRouteInput, RouteSummary } from '../types/creator'
import type { RoutePlan, RoutePlanRecord } from '../types/routePlan'
import { ApiError } from './client'
import type { RouteApi } from './types'

const samplePlan = samplePlanJson as RoutePlan

/** 公開済みとして最初から入っている 1 件（backend/out/cases/5 を publish したもの） */
export const SAMPLE_ROUTE_ID = '7298a7dd6554'

const SAMPLE_RECORD: RoutePlanRecord = {
  id: SAMPLE_ROUTE_ID,
  name: '四天王寺→てんしば',
  status: 'published',
  origin: samplePlan.origin,
  destination: samplePlan.destination,
  plan: samplePlan,
}

interface Job {
  input: CreateRouteInput
  startedAt: number
  routeId: string
}

interface FixtureState {
  records: ReadonlyMap<string, RoutePlanRecord>
  jobs: ReadonlyMap<string, Job>
}

export interface FixtureApiOptions {
  /** 現在時刻。テストで差し替える */
  now?: () => number
  /** 作成完了までの疑似待ち時間 */
  createDelayMs?: number
  /** 公開 URL の origin。ブラウザでは location.origin */
  publicOrigin?: string
  /** 最初から入っている道案内 */
  seed?: RoutePlanRecord[]
}

function withEntry<K, V>(map: ReadonlyMap<K, V>, key: K, value: V): ReadonlyMap<K, V> {
  return new Map([...map, [key, value]])
}

function toSummary(r: RoutePlanRecord): RouteSummary {
  return { id: r.id, origin: r.origin, destination: r.destination, status: r.status }
}

/** 入力の出発地・目的地だけを差し替えた写真列を作る。ステップは fixture のまま */
function planFor(input: CreateRouteInput): RoutePlan {
  return { ...samplePlan, origin: input.origin, destination: input.destination }
}

export function createFixtureApi(options: FixtureApiOptions = {}): RouteApi {
  const now = options.now ?? Date.now
  const createDelayMs = options.createDelayMs ?? FIXTURE_CREATE_DELAY_MS
  const publicOrigin = options.publicOrigin ?? globalThis.location?.origin ?? ''
  const seed = options.seed ?? [SAMPLE_RECORD]

  let state: FixtureState = {
    records: new Map(seed.map((r) => [r.id, r])),
    jobs: new Map(),
  }

  function requireRecord(routeId: string): RoutePlanRecord {
    const record = state.records.get(routeId)
    if (!record) throw new ApiError(404, { detail: `道案内が見つかりません: ${routeId}` })
    return record
  }

  return {
    async createRoute(input) {
      const jobId = crypto.randomUUID()
      const job: Job = { input, startedAt: now(), routeId: crypto.randomUUID().slice(0, 12) }
      state = { ...state, jobs: withEntry(state.jobs, jobId, job) }
      return { jobId }
    },

    async getJobStatus(jobId) {
      const job = state.jobs.get(jobId)
      if (!job) throw new ApiError(404, { detail: `ジョブが見つかりません: ${jobId}` })
      if (now() - job.startedAt < createDelayMs) return { jobId, state: 'running' }

      if (!state.records.has(job.routeId)) {
        const record: RoutePlanRecord = {
          id: job.routeId,
          name: `${job.input.origin}→${job.input.destination}`,
          status: 'draft',
          origin: job.input.origin,
          destination: job.input.destination,
          plan: planFor(job.input),
        }
        state = { ...state, records: withEntry(state.records, record.id, record) }
      }
      return { jobId, state: 'done', routeId: job.routeId }
    },

    async listRoutes() {
      return [...state.records.values()].map(toSummary)
    },

    async getRoutePlan(routeId) {
      return requireRecord(routeId)
    },

    async publishRoute(routeId) {
      const record = requireRecord(routeId)
      const published: RoutePlanRecord = { ...record, status: 'published' }
      state = { ...state, records: withEntry(state.records, routeId, published) }
      return { routeId, url: `${publicOrigin}/r/${routeId}` }
    },

    async getPublicRoutePlan(routeId) {
      const record = requireRecord(routeId)
      if (record.status !== 'published') {
        throw new ApiError(404, { detail: `公開されていない道案内です: ${routeId}` })
      }
      return record
    },
  }
}

/**
 * バックエンドなしで画面を動かすための RouteApi 実装。
 * 写真列は shared/fixtures/sampleRoutePlan.json を返し、作成・公開はメモリ上の一覧だけを更新する。
 * 本物の API は serverApi.ts。endpoints.ts の切り替え（VITE_API_MODE）で差し替える。
 */
import samplePlanJson from '../fixtures/sampleRoutePlan.json'
import { FIXTURE_CREATE_DELAY_MS, JOB_STEPS, GOAL_PHOTO_LABEL } from '../lib/constants'
import { toIsoWithOffset } from '../lib/datetime'
import { removeSteps, StepEditError } from '../lib/removeSteps'
import type { CreateRouteInput, JobStep, RouteSummary } from '../types/creator'
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

const SAMPLE_CREATED_AT = '2026-10-25T10:12:00+09:00'

/** 一覧用に作成日時と作成者を添えた 1 件。作成者が無いもの（最初から入っている分）は誰の一覧にも出る */
interface StoredRecord {
  record: RoutePlanRecord
  createdAt: string
  creatorId?: string
}

interface Job {
  input: CreateRouteInput
  startedAt: number
  routeId: string
  /** 完了を一度返して保存したか */
  saved: boolean
}

interface FixtureState {
  records: ReadonlyMap<string, StoredRecord>
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

function toSummary({ record, createdAt }: StoredRecord): RouteSummary {
  return {
    id: record.id,
    name: record.name,
    origin: record.origin,
    destination: record.destination,
    status: record.status,
    createdAt,
  }
}

/** FNV-1a（32bit）。暗号用途ではない */
function fnv1a(text: string, seed: number): number {
  let h = seed >>> 0
  for (const byte of new TextEncoder().encode(text)) {
    h = Math.imul(h ^ byte, 0x01000193) >>> 0
  }
  return h
}

/**
 * 命名から決まる 12 桁の ID。本物は SHA-256 の先頭 12 桁（interface.md 3 章）だが、
 * fixture では http の LAN 接続でも動くよう crypto.subtle を使わない簡易ハッシュにする。
 */
export function fixtureRouteId(name: string): string {
  const key = name.trim()
  const hex = (n: number) => n.toString(16).padStart(8, '0')
  return (hex(fnv1a(key, 0x811c9dc5)) + hex(fnv1a(key, 0x01000193))).slice(0, 12)
}

/** 経過時間から今の処理段階を決める（疑似） */
function stepAt(elapsedMs: number, totalMs: number): JobStep {
  const ratio = totalMs <= 0 ? 1 : elapsedMs / totalMs
  const index = Math.min(JOB_STEPS.length - 1, Math.max(0, Math.floor(ratio * JOB_STEPS.length)))
  return JOB_STEPS[index]
}

/** 目的地の表示名。省略時はバックエンドと同じく最後の写真のメッセージか既定の呼び名 */
function goalLabel(input: CreateRouteInput): string {
  const last = input.photos[input.photos.length - 1]
  return input.destination.trim() || last?.caption || GOAL_PHOTO_LABEL
}

/** 入力の出発地・目的地だけを差し替えた写真列を作る。ステップは fixture のまま */
function planFor(input: CreateRouteInput): RoutePlan {
  return { ...samplePlan, origin: input.origin, destination: goalLabel(input) }
}

export function createFixtureApi(options: FixtureApiOptions = {}): RouteApi {
  const now = options.now ?? Date.now
  const createDelayMs = options.createDelayMs ?? FIXTURE_CREATE_DELAY_MS
  const publicOrigin = options.publicOrigin ?? globalThis.location?.origin ?? ''
  const seed = options.seed ?? [SAMPLE_RECORD]

  let state: FixtureState = {
    records: new Map(seed.map((record) => [record.id, { record, createdAt: SAMPLE_CREATED_AT }])),
    jobs: new Map(),
  }

  function requireStored(routeId: string): StoredRecord {
    const stored = state.records.get(routeId)
    if (!stored) throw new ApiError(404, { detail: `道案内が見つかりません: ${routeId}` })
    return stored
  }

  function saveJobResult(job: Job) {
    const record: RoutePlanRecord = {
      id: job.routeId,
      name: job.input.name.trim(),
      status: 'draft',
      origin: job.input.origin,
      destination: goalLabel(job.input),
      plan: planFor(job.input),
    }
    const stored: StoredRecord = {
      record,
      createdAt: toIsoWithOffset(new Date(now())),
      creatorId: job.input.creatorId,
    }
    state = { ...state, records: withEntry(state.records, record.id, stored) }
  }

  return {
    async createRoute(input) {
      if (!input.name.trim()) throw new ApiError(400, { detail: 'name が空です' })
      const name = input.name.trim()
      // 最初から入っている分は本物の ID なので、名前でも突き合わせる
      const existing = [...state.records.values()].find((s) => s.record.name === name)
      const routeId = existing?.record.id ?? fixtureRouteId(name)
      if (existing?.record.status === 'published') {
        throw new ApiError(409, { detail: 'この名前の道案内は公開中なので、作り直せません。別の名前で作ってください。' })
      }
      if (existing && existing.creatorId !== input.creatorId) {
        throw new ApiError(409, { detail: `同じ名前の道が既にあります: ${input.name}` })
      }
      const jobId = crypto.randomUUID()
      const job: Job = { input, startedAt: now(), routeId, saved: false }
      state = { ...state, jobs: withEntry(state.jobs, jobId, job) }
      return { jobId, routeId }
    },

    async getJobStatus(jobId) {
      const job = state.jobs.get(jobId)
      if (!job) throw new ApiError(404, { detail: `ジョブが見つかりません: ${jobId}` })
      const elapsed = now() - job.startedAt
      if (elapsed < createDelayMs) {
        return { jobId, state: 'running', step: stepAt(elapsed, createDelayMs), routeId: null, message: null }
      }
      if (!job.saved) {
        // 同じ作成者の作り直しは同じ ID に上書きし、下書きに戻す（本物と同じ）
        saveJobResult(job)
        state = { ...state, jobs: withEntry(state.jobs, jobId, { ...job, saved: true }) }
      }
      return { jobId, state: 'done', step: 'save', routeId: job.routeId, message: null }
    },

    async listRoutes(creatorId) {
      return [...state.records.values()]
        .filter((s) => s.creatorId === undefined || s.creatorId === creatorId)
        .sort((a, b) => Date.parse(b.createdAt) - Date.parse(a.createdAt))
        .map(toSummary)
    },

    async getRoutePlan(routeId) {
      return requireStored(routeId).record
    },

    async removeSteps(routeId, creatorId, indices) {
      const stored = requireStored(routeId)
      if (stored.record.status !== 'draft') {
        throw new ApiError(409, { detail: '公開中の道案内は変更できません。' })
      }
      if (stored.creatorId === undefined || stored.creatorId !== creatorId) {
        throw new ApiError(403, { detail: 'この道案内は編集できません（作った人だけが編集できます）。' })
      }
      let plan
      try {
        plan = removeSteps(stored.record.plan, indices)
      } catch (e) {
        if (e instanceof StepEditError) throw new ApiError(400, { detail: e.message })
        throw e
      }
      const updated: StoredRecord = { ...stored, record: { ...stored.record, plan } }
      state = { ...state, records: withEntry(state.records, routeId, updated) }
      return updated.record
    },

    async publishRoute(routeId) {
      const stored = requireStored(routeId)
      const published: StoredRecord = { ...stored, record: { ...stored.record, status: 'published' } }
      state = { ...state, records: withEntry(state.records, routeId, published) }
      // QR 画像はバックエンドが描くので、fixture では URL だけ返す
      return { routeId, url: `${publicOrigin}/r/${routeId}`, qrPath: null }
    },

    async getPublicRoutePlan(routeId) {
      const { record } = requireStored(routeId)
      if (record.status !== 'published') {
        throw new ApiError(404, { detail: `公開されていない道案内です: ${routeId}` })
      }
      return record
    },
  }
}

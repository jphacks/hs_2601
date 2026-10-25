/**
 * 作る人向け API の入出力。backend/app/schemas/creator.py と 1:1 にする（バックエンド側は未作成）。
 * パスと入出力の一覧は docs/overview.md 4 章。
 */
import type { PlanStatus } from './routePlan'

/** 撮影した写真 1 枚と、撮影時の座標 */
export interface PhotoInput {
  file: File
  lat?: number
  lng?: number
}

export interface CreateRouteInput {
  origin: string
  destination: string
  photos: PhotoInput[]
  creatorId: string
}

export interface CreateRouteResult {
  jobId: string
}

export type JobState = 'running' | 'done' | 'failed'

export interface JobStatus {
  jobId: string
  state: JobState
  /** 完了時にだけ入る */
  routeId?: string
  /** 失敗時にだけ入る */
  message?: string
}

/** 一覧取得 API の 1 件 */
export interface RouteSummary {
  id: string
  origin: string
  destination: string
  status: PlanStatus
}

export interface PublishResult {
  routeId: string
  /** 参加者に渡す URL */
  url: string
}

/** 5 本の API を関数にしたインターフェース。fixture 実装と server 実装が同じ形を持つ */
import type {
  CreateRouteInput,
  CreateRouteResult,
  JobStatus,
  PublishResult,
  RouteSummary,
} from '../types/creator'
import type { RoutePlanRecord } from '../types/routePlan'

export interface RouteApi {
  /** 作成受付: 出発地・目的地・写真と座標・作成者 ID → ジョブ ID */
  createRoute(input: CreateRouteInput): Promise<CreateRouteResult>
  /** ステータス取得: ジョブ ID → 作成中 / 完了 / 失敗 */
  getJobStatus(jobId: string): Promise<JobStatus>
  /** 一覧取得: 作成者 ID → 道案内の一覧 */
  listRoutes(creatorId: string): Promise<RouteSummary[]>
  /** 詳細取得: 道案内 ID → 写真列 JSON（作る人の確認画面用。下書きも返す） */
  getRoutePlan(routeId: string): Promise<RoutePlanRecord>
  /**
   * 写真を外す: 写真列から、並び順（0 始まり）で選んだ地点を外す。公開中でも外せる（公開のまま）。
   * ゴールの写真・他の作成者の道案内は変えない（エラーになる）
   */
  removeSteps(routeId: string, creatorId: string, indices: number[]): Promise<RoutePlanRecord>
  /** 公開: 道案内 ID → 公開 URL */
  publishRoute(routeId: string): Promise<PublishResult>
  /** 参加者向け詳細取得: 公開済みのものだけ返す */
  getPublicRoutePlan(routeId: string): Promise<RoutePlanRecord>
}

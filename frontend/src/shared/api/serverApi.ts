/**
 * FastAPI バックエンドを呼ぶ RouteApi 実装。契約は docs/interface.md 5 章。
 */
import { toIsoWithOffset } from '../lib/datetime'
import type { CreateRouteResult, JobStatus, PublishResult, RouteSummary } from '../types/creator'
import type { RoutePlanRecord } from '../types/routePlan'
import { api } from './client'
import { buildPlanManifest, photoFileName } from './planManifest'
import type { RouteApi } from './types'

const id = encodeURIComponent

export const serverApi: RouteApi = {
  createRoute(input) {
    const manifest = buildPlanManifest(input, toIsoWithOffset(new Date()))
    const form = new FormData()
    form.append('manifest', JSON.stringify(manifest))
    input.photos.forEach((p) => form.append('photos', p.file, photoFileName(p.id)))
    return api.post<CreateRouteResult>('/api/routes', form)
  },
  getJobStatus(jobId) {
    return api.get<JobStatus>(`/api/jobs/${id(jobId)}`)
  },
  listRoutes(creatorId) {
    return api.get<RouteSummary[]>(`/api/routes?creator_id=${id(creatorId)}`)
  },
  getRoutePlan(routeId) {
    return api.get<RoutePlanRecord>(`/api/routes/${id(routeId)}`)
  },
  publishRoute(routeId) {
    return api.post<PublishResult>(`/api/routes/${id(routeId)}/publish`)
  },
  getPublicRoutePlan(routeId) {
    return api.get<RoutePlanRecord>(`/api/public/routes/${id(routeId)}`)
  },
}

/**
 * FastAPI バックエンドを呼ぶ RouteApi 実装。
 * パスは暫定（backend/app/api/creator.py、follower.py が未実装）。バックエンドが決まったらここだけ直す。
 */
import type { CreateRouteResult, JobStatus, PublishResult, RouteSummary } from '../types/creator'
import type { RoutePlanRecord } from '../types/routePlan'
import { api } from './client'
import type { RouteApi } from './types'

export const serverApi: RouteApi = {
  createRoute(input) {
    const form = new FormData()
    form.append('origin', input.origin)
    form.append('destination', input.destination)
    form.append('creator_id', input.creatorId)
    input.photos.forEach((p, i) => {
      form.append('photos', p.file)
      form.append(`photo_lat_${i}`, p.lat === undefined ? '' : String(p.lat))
      form.append(`photo_lng_${i}`, p.lng === undefined ? '' : String(p.lng))
    })
    return api.post<CreateRouteResult>('/api/routes', form)
  },
  getJobStatus(jobId) {
    return api.get<JobStatus>(`/api/jobs/${encodeURIComponent(jobId)}`)
  },
  listRoutes(creatorId) {
    return api.get<RouteSummary[]>(`/api/routes?creator_id=${encodeURIComponent(creatorId)}`)
  },
  getRoutePlan(routeId) {
    return api.get<RoutePlanRecord>(`/api/routes/${encodeURIComponent(routeId)}`)
  },
  publishRoute(routeId) {
    return api.post<PublishResult>(`/api/routes/${encodeURIComponent(routeId)}/publish`)
  },
  getPublicRoutePlan(routeId) {
    return api.get<RoutePlanRecord>(`/api/public/routes/${encodeURIComponent(routeId)}`)
  },
}

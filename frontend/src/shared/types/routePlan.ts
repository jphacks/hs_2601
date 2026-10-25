/**
 * 写真列 JSON（RoutePlan）の型。
 * backend/app/schemas/route_plan.py と 1:1 で対応させる。片方を変えたら必ずもう片方も変える。
 */

export type Turn = 'left' | 'right' | 'straight' | 'arrive'

export type PlanStatus = 'draft' | 'published'

export interface RouteStep {
  index: number
  lat: number
  lng: number
  turn: Turn
  instruction: string
  landmark: string | null
  distance_to_next_m: number
  /** 矢印入り画像の公開 URL。画像が無い地点は null */
  image_url: string | null
}

export interface RoutePlan {
  version: 1
  origin: string
  destination: string
  polyline: string
  total_distance_m: number
  steps: RouteStep[]
}

/** DB の 1 行（RoutePlanRecord）。詳細取得 API が返す */
export interface RoutePlanRecord {
  id: string
  name: string
  status: PlanStatus
  origin: string
  destination: string
  plan: RoutePlan
}

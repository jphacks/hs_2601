/**
 * 写真列から地点を外す（バックエンドの app/services/creator/edit_steps.py と同じ規則）。
 * fixture の API と、画面の事前チェックで使う。元の plan は変更しない。
 */
import type { RoutePlan, RouteStep } from '../types/routePlan'

export class StepEditError extends Error {
  constructor(message: string) {
    super(message)
    this.name = 'StepEditError'
  }
}

/** 外した地点の「次まで」の距離は直前に残る地点へ足す。ゴール（最後）は外せない */
export function removeSteps(plan: RoutePlan, indices: readonly number[]): RoutePlan {
  const n = plan.steps.length
  const targets = new Set(indices)
  if (targets.size === 0) throw new StepEditError('外す写真を選んでください。')
  if ([...targets].some((i) => i < 0 || i >= n)) {
    throw new StepEditError('存在しない写真が指定されています。画面を読み込み直してください。')
  }
  if (targets.has(n - 1)) throw new StepEditError('ゴールの写真は外せません。')

  const kept = plan.steps.reduce<RouteStep[]>((acc, step, i) => {
    if (!targets.has(i)) return [...acc, step]
    if (acc.length === 0) return acc
    const prev = acc[acc.length - 1]
    return [...acc.slice(0, -1), { ...prev, distance_to_next_m: prev.distance_to_next_m + step.distance_to_next_m }]
  }, [])
  return { ...plan, steps: kept.map((s, k) => ({ ...s, index: k })) }
}

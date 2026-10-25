import { describe, expect, it } from 'vitest'
import type { RoutePlan, RouteStep, Turn } from '../types/routePlan'
import { removeSteps, StepEditError } from './removeSteps'

function plan(distances: number[]): RoutePlan {
  const steps: RouteStep[] = distances.map((d, i) => ({
    index: i,
    lat: 0,
    lng: 0,
    turn: (i === distances.length - 1 ? 'arrive' : 'left') as Turn,
    instruction: '',
    landmark: null,
    distance_to_next_m: d,
    image_url: `u${i}`,
  }))
  return { version: 1, origin: 'a', destination: 'b', polyline: '', total_distance_m: 0, steps }
}

describe('removeSteps', () => {
  it('選んだ地点を外し、距離を直前に足して番号を振り直す', () => {
    const p = plan([100, 20, 30, 50, 0])
    const out = removeSteps(p, [1, 2])
    expect(out.steps.map((s) => s.image_url)).toEqual(['u0', 'u3', 'u4'])
    expect(out.steps.map((s) => s.distance_to_next_m)).toEqual([150, 50, 0])
    expect(out.steps.map((s) => s.index)).toEqual([0, 1, 2])
    expect(p.steps).toHaveLength(5) // 元は変えない
  })

  it('ゴール・範囲外・空は外せない', () => {
    const p = plan([100, 20, 0])
    expect(() => removeSteps(p, [2])).toThrow(StepEditError)
    expect(() => removeSteps(p, [7])).toThrow(StepEditError)
    expect(() => removeSteps(p, [])).toThrow(StepEditError)
  })
})

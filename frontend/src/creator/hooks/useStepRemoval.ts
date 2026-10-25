import { useState } from 'react'
import { apiErrorMessage } from '../../shared/api/errors'
import { routeApi } from '../../shared/api/endpoints'
import type { RoutePlanRecord } from '../../shared/types/routePlan'
import { getOrCreateCreatorId } from '../storage/creatorId'

export interface StepRemoval {
  /** 選んでいる写真（写真列の並び順、0 始まり） */
  selected: ReadonlySet<number>
  toggle: (index: number) => void
  clear: () => void
  busy: boolean
  error: string | null
  /** 選んだ写真を外す。成功すれば更新後の行を返す */
  remove: () => Promise<RoutePlanRecord | null>
}

/** 下書きの写真列から写真を選んで外す。公開中の道案内はバックエンドが拒否する */
export function useStepRemoval(record: RoutePlanRecord): StepRemoval {
  const [selected, setSelected] = useState<ReadonlySet<number>>(new Set())
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  function toggle(index: number) {
    setSelected((prev) => {
      const next = new Set(prev)
      if (next.has(index)) next.delete(index)
      else next.add(index)
      return next
    })
  }

  async function remove(): Promise<RoutePlanRecord | null> {
    if (selected.size === 0 || busy) return null
    setBusy(true)
    setError(null)
    try {
      const updated = await routeApi.removeSteps(record.id, getOrCreateCreatorId(), [...selected].sort((a, b) => a - b))
      setSelected(new Set())
      return updated
    } catch (e) {
      setError(apiErrorMessage(e, '写真を外せませんでした'))
      return null
    } finally {
      setBusy(false)
    }
  }

  return { selected, toggle, clear: () => setSelected(new Set()), busy, error, remove }
}

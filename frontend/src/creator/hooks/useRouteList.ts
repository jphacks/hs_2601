import { useEffect, useState } from 'react'
import { routeApi } from '../../shared/api/endpoints'
import type { PublishResult, RouteSummary } from '../../shared/types/creator'
import { getOrCreateCreatorId } from '../storage/creatorId'

/** 自分の道案内一覧の取得、チェック選択、選んだものの公開 */
export function useRouteList(
  onPublished: (results: PublishResult[], routes: RouteSummary[]) => void,
) {
  const [routes, setRoutes] = useState<RouteSummary[]>([])
  const [selected, setSelected] = useState<string[]>([])
  const [loading, setLoading] = useState(true)
  const [publishing, setPublishing] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    routeApi
      .listRoutes(getOrCreateCreatorId())
      .then((list) => {
        if (!cancelled) setRoutes(list)
      })
      .catch((e: unknown) => {
        if (!cancelled) setError(e instanceof Error ? e.message : '一覧を取得できませんでした')
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [])

  function toggleSelected(routeId: string, checked: boolean) {
    setSelected((old) => (checked ? [...old, routeId] : old.filter((id) => id !== routeId)))
  }

  async function publishSelected() {
    if (selected.length === 0) return
    setPublishing(true)
    setError(null)
    try {
      const results = await Promise.all(selected.map((id) => routeApi.publishRoute(id)))
      setSelected([])
      onPublished(results, routes)
    } catch (e) {
      setError(e instanceof Error ? e.message : '公開に失敗しました')
    } finally {
      setPublishing(false)
    }
  }

  return { routes, selected, loading, publishing, error, toggleSelected, publishSelected }
}

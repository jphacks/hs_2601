import { useNavigate } from 'react-router-dom'
import type { PublishResult, RouteSummary } from '../../shared/types/creator'
import { RoutePublishList } from '../components/RoutePublishList'
import { useRouteList } from '../hooks/useRouteList'

/** 公開完了画面に navigate state で渡す値 */
export interface PublishedState {
  results: PublishResult[]
  /** routeId → 道の名前 */
  labels: Record<string, string>
}

function labelsFor(routes: RouteSummary[], results: PublishResult[]): Record<string, string> {
  return Object.fromEntries(
    results.map((r) => [r.routeId, routes.find((x) => x.id === r.routeId)?.name ?? r.routeId]),
  )
}

/** 作った道の一覧。チェックして公開する */
export function RouteListPage() {
  const navigate = useNavigate()
  const list = useRouteList((results, routes) => {
    const state: PublishedState = { results, labels: labelsFor(routes, results) }
    navigate('/c/published', { state })
  })

  return (
    <RoutePublishList
      routes={list.routes}
      selected={list.selected}
      loading={list.loading}
      publishing={list.publishing}
      error={list.error}
      onToggle={list.toggleSelected}
      onDetail={(route) => navigate(`/c/routes/${route.id}`)}
      onPublish={list.publishSelected}
    />
  )
}

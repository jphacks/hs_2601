import { Navigate, useLocation, useNavigate } from 'react-router-dom'
import { apiUrl } from '../../shared/api/client'
import { RoutePublished, type PublishedItem } from '../components/RoutePublished'
import { useCopy } from '../hooks/useCopy'
import type { PublishedState } from './RouteListPage'

function isPublishedState(v: unknown): v is PublishedState {
  return typeof v === 'object' && v !== null && Array.isArray((v as PublishedState).results)
}

function toItems({ results, labels }: PublishedState): PublishedItem[] {
  return results.map((r) => ({
    routeId: r.routeId,
    name: labels[r.routeId] ?? r.routeId,
    url: r.url,
    qrSrc: r.qrPath ? apiUrl(r.qrPath) : null,
  }))
}

/** 公開完了。一覧ページから渡された結果を表示する。直接開かれたら一覧へ戻す */
export function PublishedPage() {
  const navigate = useNavigate()
  const { state } = useLocation()
  const clipboard = useCopy()

  if (!isPublishedState(state)) return <Navigate to="/c/routes" replace />

  return (
    <RoutePublished
      items={toItems(state)}
      copiedId={clipboard.copiedKey}
      copyError={clipboard.error}
      onCopy={(item) => clipboard.copy(item.routeId, item.url)}
      onHome={() => navigate('/c')}
    />
  )
}

import { Navigate, useLocation, useNavigate } from 'react-router-dom'
import { RoutePublished } from '../components/RoutePublished'
import type { PublishedState } from './RouteListPage'

function isPublishedState(v: unknown): v is PublishedState {
  return typeof v === 'object' && v !== null && Array.isArray((v as PublishedState).results)
}

/** 公開完了。一覧ページから渡された結果を表示する。直接開かれたら一覧へ戻す */
export function PublishedPage() {
  const navigate = useNavigate()
  const { state } = useLocation()

  if (!isPublishedState(state)) return <Navigate to="/c/routes" replace />

  return <RoutePublished results={state.results} labels={state.labels} onHome={() => navigate('/c')} />
}

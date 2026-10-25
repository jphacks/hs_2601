import { useNavigate, useParams } from 'react-router-dom'
import { RouteDetail } from '../components/RouteDetail'
import { RouteLoading } from '../components/RouteLoading'
import { secondaryClass } from '../components/styles'
import { useRoutePlan } from '../hooks/useRoutePlan'

/** 作成結果の確認・道の詳細表示（共通）。RoutePlanViewer で写真列を描く */
export function ResultPage() {
  const { routeId } = useParams<{ routeId: string }>()
  const navigate = useNavigate()
  const state = useRoutePlan(routeId)

  if (state.status === 'loading') return <RouteLoading />
  if (state.status === 'error') {
    return (
      <section className="space-y-4 py-10 text-center">
        <p role="alert" className="text-sm text-red-700">
          {state.message}
        </p>
        <button className={secondaryClass} onClick={() => navigate('/c/routes')}>
          一覧に戻る
        </button>
      </section>
    )
  }

  return (
    <RouteDetail
      record={state.value}
      onPublish={() => navigate('/c/routes')}
      onEdit={() => navigate('/c/new')}
    />
  )
}

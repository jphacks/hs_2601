import { useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import type { RoutePlanRecord } from '../../shared/types/routePlan'
import { RouteDetail } from '../components/RouteDetail'
import { RouteLoading } from '../components/RouteLoading'
import { secondaryClass } from '../components/styles'
import { useRoutePlan } from '../hooks/useRoutePlan'

/** 作成結果の確認・道の詳細表示（共通）。RoutePlanViewer で写真列を描く */
export function ResultPage() {
  const { routeId } = useParams<{ routeId: string }>()
  const navigate = useNavigate()
  const state = useRoutePlan(routeId)
  // 写真を外した後の行。取得し直さずに画面へ反映する
  const [edited, setEdited] = useState<RoutePlanRecord | null>(null)

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
      record={edited?.id === state.value.id ? edited : state.value}
      onPublish={() => navigate('/c/routes')}
      onEdit={() => navigate('/c/new')}
      onRecordChange={setEdited}
    />
  )
}

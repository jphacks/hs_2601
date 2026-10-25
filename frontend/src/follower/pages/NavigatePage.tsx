import { useParams } from 'react-router-dom'
import { API_MODE } from '../../shared/api/endpoints'
import { RoutePlanViewer } from '../../shared/components/RoutePlanViewer'
import { NavigateHeader } from '../components/NavigateHeader'
import { useRoutePlan } from '../hooks/useRoutePlan'

/** 道案内表示画面。URL の ID で写真列を取得し、RoutePlanViewer で描く */
export function NavigatePage() {
  const { id } = useParams<{ id: string }>()
  const state = useRoutePlan(id)

  return (
    <main className="box-border min-h-screen bg-canvas px-4 pt-5 pb-8 text-ink">
      <div className="mx-auto max-w-[480px]">
        {state.status === 'loading' && (
          <p className="py-20 text-center text-sm text-muted">道案内を読み込んでいます...</p>
        )}
        {state.status === 'error' && (
          <p className="py-20 text-center text-sm text-red-600">{state.message}</p>
        )}
        {state.status === 'ready' && (
          <>
            <NavigateHeader
              origin={state.value.origin}
              destination={state.value.destination}
              routeId={state.value.id}
              demo={API_MODE === 'fixture'}
            />
            <RoutePlanViewer plan={state.value.plan} />
            {API_MODE === 'fixture' && (
              <p className="mt-[18px] text-center text-[11px] leading-[1.7] text-muted-soft">
                ※ 現在は画面確認用のサンプルです。写真・距離・経路は実際の道順ではありません。
              </p>
            )}
          </>
        )}
      </div>
    </main>
  )
}

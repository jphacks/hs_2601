import { useEffect } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { RouteLoading } from '../components/RouteLoading'
import { secondaryClass } from '../components/styles'
import { useJobPolling } from '../hooks/useJobPolling'

/** 作成中。ステータスをポーリングし、完了したら確認画面へ */
export function CreatingPage() {
  const { jobId } = useParams<{ jobId: string }>()
  const navigate = useNavigate()
  const polling = useJobPolling(jobId)

  useEffect(() => {
    if (polling.status === 'done') navigate(`/c/routes/${polling.routeId}`, { replace: true })
  }, [polling, navigate])

  if (polling.status === 'failed') {
    return (
      <section className="space-y-4 py-10 text-center">
        <h1 className="text-xl font-bold">作成に失敗しました</h1>
        <p role="alert" className="text-sm text-red-700">
          {polling.message}
        </p>
        <button className={secondaryClass} onClick={() => navigate('/c/new')}>
          写真一覧に戻る
        </button>
      </section>
    )
  }

  return <RouteLoading />
}

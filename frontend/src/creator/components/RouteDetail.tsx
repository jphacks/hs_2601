import { RoutePlanViewer } from '../../shared/components/RoutePlanViewer'
import type { RoutePlanRecord } from '../../shared/types/routePlan'
import { buttonClass, secondaryClass } from './styles'

interface Props {
  record: RoutePlanRecord
  onPublish: () => void
  onEdit: () => void
}

/** 作成した道案内の確認画面。写真列は参加者画面と同じ RoutePlanViewer で描く */
export function RouteDetail({ record, onPublish, onEdit }: Props) {
  return (
    <section className="space-y-5">
      <h1 className="text-2xl font-bold">道案内の確認</h1>
      <div className="rounded-2xl border bg-white p-4">
        <p className="text-sm text-stone-500">出発地</p>
        <p className="font-semibold">{record.origin}</p>
        <p className="my-2 text-emerald-700">↓</p>
        <p className="text-sm text-stone-500">目的地</p>
        <p className="font-semibold">{record.destination}</p>
        <p className="mt-2 text-xs text-stone-500">
          {record.status === 'published' ? '公開済み' : '下書き'}
        </p>
      </div>

      <RoutePlanViewer plan={record.plan} />

      <button className={buttonClass} onClick={onPublish}>
        公開画面へ
      </button>
      <button className={secondaryClass} onClick={onEdit}>
        写真を追加・修正する
      </button>
    </section>
  )
}

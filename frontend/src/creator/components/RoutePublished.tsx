import type { PublishResult } from '../../shared/types/creator'
import { buttonClass } from './styles'

interface Props {
  /** 公開した道と参加者向け URL */
  results: PublishResult[]
  /** 公開した道の表示名（出発地 → 目的地）。routeId → 表示名 */
  labels: Record<string, string>
  onHome: () => void
}

/** 公開完了画面。参加者に渡す URL を表示する（QR は今後） */
export function RoutePublished({ results, labels, onHome }: Props) {
  return (
    <section className="space-y-4 rounded-2xl border bg-white p-5">
      <h1 className="text-2xl font-bold">公開処理が完了しました</h1>
      <p className="text-sm text-stone-600">
        下の URL を参加者に渡してください。
      </p>
      {results.map((r) => (
        <div key={r.routeId} className="rounded-xl bg-stone-50 p-3">
          <p className="font-semibold">{labels[r.routeId] ?? r.routeId}</p>
          <a
            href={r.url}
            target="_blank"
            rel="noreferrer"
            className="mt-1 block text-sm break-all text-emerald-700 underline"
          >
            {r.url}
          </a>
        </div>
      ))}
      <button className={buttonClass} onClick={onHome}>
        ホームへ戻る
      </button>
    </section>
  )
}

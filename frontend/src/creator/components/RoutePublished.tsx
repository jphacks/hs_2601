import type { Route } from '../types'
import { buttonClass } from './styles'

interface Props {
  /** 公開対象として選ばれた道 */
  routes: Route[]
  onHome: () => void
}

/** 公開完了画面 */
export function RoutePublished({ routes, onHome }: Props) {
  return (
    <section className="space-y-4 rounded-2xl border bg-white p-5">
      <h1 className="text-2xl font-bold">公開処理が完了しました</h1>
      <p className="text-sm text-stone-600">
        現在は画面確認用です。実際の共有 URL はバックエンド接続後に発行します。
      </p>
      {routes.map((r) => (
        <div key={r.id} className="rounded-xl bg-stone-50 p-3">
          <p className="font-semibold">
            {r.start} → {r.goal}
          </p>
          <p className="mt-1 text-sm text-emerald-700">公開済み（試作）</p>
        </div>
      ))}
      <button className={buttonClass} onClick={onHome}>
        ホームへ戻る
      </button>
    </section>
  )
}

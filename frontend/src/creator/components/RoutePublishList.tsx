import type { Route } from '../types'
import { buttonClass } from './styles'

interface Props {
  routes: Route[]
  selected: string[]
  onToggle: (routeId: string, checked: boolean) => void
  onDetail: (route: Route) => void
  onPublish: () => void
}

/** 「作った道を公開する」画面。公開する道をチェックして選ぶ */
export function RoutePublishList({ routes, selected, onToggle, onDetail, onPublish }: Props) {
  return (
    <section className="space-y-4">
      <h1 className="text-2xl font-bold">作った道を公開する</h1>
      {routes.length === 0 ? (
        <p className="rounded-xl bg-white p-5 text-sm text-stone-500">
          まだ道案内がありません。まず「道を作る」から作成してください。
        </p>
      ) : (
        routes.map((route) => (
          <label key={route.id} className="flex items-start gap-3 rounded-xl border bg-white p-4">
            <input
              type="checkbox"
              className="mt-1 h-5 w-5 accent-emerald-700"
              checked={selected.includes(route.id)}
              onChange={(e) => onToggle(route.id, e.target.checked)}
            />
            <span className="flex-1">
              <span className="block font-semibold">
                {route.start} → {route.goal}
              </span>
              <span className="mt-1 block text-sm text-stone-500">
                {route.published ? '公開済み' : '下書き'}
              </span>
              <button
                className="mt-2 text-sm text-emerald-700 underline"
                onClick={(e) => {
                  e.preventDefault()
                  onDetail(route)
                }}
              >
                詳細を見る
              </button>
            </span>
          </label>
        ))
      )}
      <button className={buttonClass} disabled={selected.length === 0} onClick={onPublish}>
        選択した道を公開する
      </button>
    </section>
  )
}

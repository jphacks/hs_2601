import { formatDateTime } from '../../shared/lib/datetime'
import type { RouteSummary } from '../../shared/types/creator'
import { buttonClass } from './styles'

interface Props {
  routes: RouteSummary[]
  selected: string[]
  loading: boolean
  publishing: boolean
  error: string | null
  onToggle: (routeId: string, checked: boolean) => void
  onDetail: (route: RouteSummary) => void
  onPublish: () => void
}

/** 「作った道を公開する」画面。公開する道をチェックして選ぶ */
export function RoutePublishList({
  routes,
  selected,
  loading,
  publishing,
  error,
  onToggle,
  onDetail,
  onPublish,
}: Props) {
  return (
    <section className="space-y-4">
      <h1 className="text-2xl font-bold">作った道を公開する</h1>
      {loading && <p className="text-sm text-stone-500">読み込んでいます...</p>}
      {!loading && routes.length === 0 && (
        <p className="rounded-xl bg-white p-5 text-sm text-stone-500">
          まだ道案内がありません。まず「道を作る」から作成してください。
        </p>
      )}
      {routes.map((route) => (
        <div key={route.id} className="flex items-start gap-3 rounded-xl border bg-white p-4">
          <input
            id={`route-${route.id}`}
            type="checkbox"
            className="mt-1 h-5 w-5 accent-emerald-700"
            checked={selected.includes(route.id)}
            onChange={(e) => onToggle(route.id, e.target.checked)}
          />
          <div className="flex-1">
            <label htmlFor={`route-${route.id}`} className="block font-semibold break-all">
              {route.name}
            </label>
            <span className="mt-1 block text-sm text-stone-600">
              {route.origin} → {route.destination}
            </span>
            <span className="mt-1 flex items-center gap-2 text-xs text-stone-500">
              <span
                className={`rounded-full px-2 py-0.5 font-semibold ${
                  route.status === 'published'
                    ? 'bg-emerald-100 text-emerald-800'
                    : 'bg-stone-200 text-stone-700'
                }`}
              >
                {route.status === 'published' ? '公開済み' : '下書き'}
              </span>
              <time dateTime={route.createdAt}>{formatDateTime(route.createdAt)}</time>
            </span>
            <button
              className="mt-2 text-sm text-emerald-700 underline"
              onClick={() => onDetail(route)}
            >
              詳細を見る
            </button>
          </div>
        </div>
      ))}
      {error && (
        <p role="alert" className="rounded-xl bg-red-50 px-4 py-3 text-sm text-red-700">
          {error}
        </p>
      )}
      <button
        className={`${buttonClass} disabled:opacity-50`}
        disabled={selected.length === 0 || publishing}
        onClick={onPublish}
      >
        {publishing ? '公開しています...' : '選択した道を公開する（QR を表示）'}
      </button>
    </section>
  )
}

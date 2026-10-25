import { buttonClass } from './styles'

/** 公開した道 1 件の表示内容 */
export interface PublishedItem {
  routeId: string
  /** 道の名前（命名） */
  name: string
  /** 参加者に渡す URL */
  url: string
  /** QR 画像の URL。無ければ URL だけ出す */
  qrSrc: string | null
}

interface Props {
  items: PublishedItem[]
  /** コピー済みの routeId（「コピーしました」表示用） */
  copiedId: string | null
  /** コピーに失敗したときの案内。なければ null */
  copyError: string | null
  onCopy: (item: PublishedItem) => void
  onHome: () => void
}

/** 公開完了画面。参加者に渡す QR・ID・URL を表示する */
export function RoutePublished({ items, copiedId, copyError, onCopy, onHome }: Props) {
  return (
    <section className="space-y-4 rounded-2xl border bg-white p-5">
      <h1 className="text-2xl font-bold">公開しました</h1>
      <p className="text-sm text-stone-600">
        QR コードを読み取ってもらうか、URL・ID を参加者に渡してください。
      </p>
      {items.map((item) => (
        <div key={item.routeId} className="space-y-3 rounded-xl bg-stone-50 p-4">
          <p className="text-lg font-semibold break-all">{item.name}</p>
          {item.qrSrc && (
            <img
              src={item.qrSrc}
              alt={`${item.name} の QR コード`}
              className="mx-auto h-56 w-56 rounded-lg bg-white p-2"
            />
          )}
          <dl className="space-y-2 text-sm">
            <div>
              <dt className="text-xs text-stone-500">ID</dt>
              <dd className="font-mono text-base tracking-wider">{item.routeId}</dd>
            </div>
            <div>
              <dt className="text-xs text-stone-500">URL</dt>
              <dd>
                <a
                  href={item.url}
                  target="_blank"
                  rel="noreferrer"
                  className="block break-all text-emerald-700 underline"
                >
                  {item.url}
                </a>
              </dd>
            </div>
          </dl>
          <button
            className="w-full rounded-lg border border-emerald-700 bg-white px-3 py-2 text-sm font-semibold text-emerald-700"
            onClick={() => onCopy(item)}
          >
            {copiedId === item.routeId ? 'コピーしました' : 'URL をコピー'}
          </button>
        </div>
      ))}
      {copyError && (
        <p role="alert" className="rounded-xl bg-red-50 px-4 py-3 text-sm text-red-700">
          {copyError}
        </p>
      )}
      <button className={buttonClass} onClick={onHome}>
        ホームへ戻る
      </button>
    </section>
  )
}

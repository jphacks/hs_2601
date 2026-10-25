interface Props {
  routeId: string
  /** 画面確認用に用意しているサンプルの ID。fixture モードのときだけ渡す */
  sampleRouteId: string | null
  /** QR 読み取り結果が道案内のものでなかったときなどの表示 */
  error: string | null
  onRouteIdChange: (value: string) => void
  onOpen: () => void
  onOpenSample: () => void
  onScanQr: () => void
}

const primaryClass =
  'w-full rounded-[14px] bg-brand px-2.5 py-4 text-base font-bold text-white disabled:cursor-not-allowed disabled:opacity-50'
const secondaryClass =
  'w-full rounded-[14px] border border-line-strong bg-white px-2.5 py-4 text-base font-bold text-brand'

/** 入口画面。QR 読み取りか ID 入力で表示画面へ進む（本番は配布 URL から直接 /r/:id に着く） */
export function EntryForm({
  routeId,
  sampleRouteId,
  error,
  onRouteIdChange,
  onOpen,
  onOpenSample,
  onScanQr,
}: Props) {
  return (
    <section>
      <div className="text-xs font-extrabold tracking-[3px] text-brand">WAYFINDER</div>
      <div className="mt-1 text-xs text-muted">写真でつなぐ道案内</div>

      <h1 className="mt-6 mb-1.5 text-2xl">道案内を開く</h1>
      <p className="m-0 text-sm text-muted">
        配布された QR コードを読み取るか、案内 ID を入力してください。
      </p>

      <button onClick={onScanQr} className={`${primaryClass} mt-6`}>
        📷 QR コードを読み取る
      </button>

      {error && (
        <p role="alert" className="mt-3 rounded-xl bg-red-50 px-4 py-3 text-sm text-red-700">
          {error}
        </p>
      )}

      <form
        className="mt-6 space-y-3"
        onSubmit={(e) => {
          e.preventDefault()
          onOpen()
        }}
      >
        <label className="block space-y-2">
          <span className="text-sm font-semibold">案内ID を直接入力</span>
          <input
            className="w-full rounded-[14px] border border-line-strong bg-white px-4 py-3"
            value={routeId}
            onChange={(e) => onRouteIdChange(e.target.value)}
            placeholder="例：7298a7dd6554"
            autoCapitalize="off"
            autoCorrect="off"
          />
        </label>
        <button type="submit" disabled={routeId.trim().length === 0} className={secondaryClass}>
          道案内を表示する
        </button>
      </form>

      {sampleRouteId && (
        <button onClick={onOpenSample} className={`${secondaryClass} mt-3`}>
          サンプルの道案内を開く
        </button>
      )}
    </section>
  )
}

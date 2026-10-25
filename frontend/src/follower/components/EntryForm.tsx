interface Props {
  routeId: string
  /** 画面確認用に用意しているサンプルの ID。fixture モードのときだけ渡す */
  sampleRouteId: string | null
  onRouteIdChange: (value: string) => void
  onOpen: () => void
  onOpenSample: () => void
}

/** 入口画面。道案内 ID を入力して表示画面へ進む（デモ用。本番は配布 URL から直接 /r/:id に着く） */
export function EntryForm({ routeId, sampleRouteId, onRouteIdChange, onOpen, onOpenSample }: Props) {
  return (
    <section>
      <div className="text-xs font-extrabold tracking-[3px] text-brand">WAYFINDER</div>
      <div className="mt-1 text-xs text-muted">写真でつなぐ道案内</div>

      <h1 className="mt-6 mb-1.5 text-2xl">道案内を開く</h1>
      <p className="m-0 text-sm text-muted">
        配布された QR コードか URL から開くと、この画面を通らずに道案内が表示されます。
      </p>

      <form
        className="mt-6 space-y-3"
        onSubmit={(e) => {
          e.preventDefault()
          onOpen()
        }}
      >
        <label className="block space-y-2">
          <span className="text-sm font-semibold">案内ID</span>
          <input
            className="w-full rounded-[14px] border border-line-strong bg-white px-4 py-3"
            value={routeId}
            onChange={(e) => onRouteIdChange(e.target.value)}
            placeholder="例：7298a7dd6554"
            autoCapitalize="off"
            autoCorrect="off"
          />
        </label>
        <button
          type="submit"
          disabled={routeId.trim().length === 0}
          className="w-full rounded-[14px] bg-brand px-2.5 py-4 text-base font-bold text-white disabled:cursor-not-allowed disabled:opacity-50"
        >
          道案内を表示する
        </button>
      </form>

      {sampleRouteId && (
        <button
          onClick={onOpenSample}
          className="mt-3 w-full rounded-[14px] border border-line-strong bg-white px-2.5 py-4 text-base font-bold text-brand"
        >
          サンプルの道案内を開く
        </button>
      )}
    </section>
  )
}

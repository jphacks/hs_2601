interface Props {
  origin: string
  destination: string
  routeId: string
  /** 画面確認用のサンプルを表示しているときに DEMO バッジを出す */
  demo: boolean
}

/** 参加者画面のヘッダー。ロゴ、タイトル、出発地 → 目的地、案内 ID */
export function NavigateHeader({ origin, destination, routeId, demo }: Props) {
  return (
    <header>
      <div className="flex items-center justify-between">
        <div>
          <div className="text-xs font-extrabold tracking-[3px] text-brand">WAYFINDER</div>
          <div className="mt-1 text-xs text-muted">写真でつなぐ道案内</div>
        </div>
        {demo && (
          <span className="rounded-[20px] bg-brand-soft px-2.5 py-1.5 text-[11px] font-bold text-brand">
            DEMO
          </span>
        )}
      </div>

      <h1 className="mt-6 mb-1.5 text-2xl">会場までの道案内</h1>
      <p className="m-0 text-sm text-muted">
        {origin} → {destination}
      </p>
      <p className="mt-1.5 text-[11px] text-muted">案内ID：{routeId}</p>
    </header>
  )
}

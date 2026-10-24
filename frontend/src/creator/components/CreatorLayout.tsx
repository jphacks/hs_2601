import type { ReactNode } from 'react'

interface Props {
  /** ホーム画面ではヘッダー右の「ホームへ」を出さない */
  showHomeLink: boolean
  onHome: () => void
  children: ReactNode
}

/** creator 全画面共通の枠とヘッダー */
export function CreatorLayout({ showHomeLink, onHome, children }: Props) {
  return (
    <main className="min-h-screen bg-stone-50 px-4 py-6 text-stone-900">
      <div className="mx-auto max-w-lg">
        <header className="mb-7 flex items-center justify-between">
          <button onClick={onHome} className="text-left">
            <p className="text-sm font-bold tracking-widest text-emerald-700">
              WAYFINDER
            </p>
            <p className="text-xs text-stone-500">写真でつなぐ道案内</p>
          </button>
          {showHomeLink && (
            <button onClick={onHome} className="text-sm text-stone-500">
              ホームへ
            </button>
          )}
        </header>
        {children}
      </div>
    </main>
  )
}

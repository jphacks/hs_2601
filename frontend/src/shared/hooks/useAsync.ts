import { useEffect, useState } from 'react'

export type AsyncState<T> =
  | { status: 'loading' }
  | { status: 'error'; message: string }
  | { status: 'ready'; value: T }

interface Loaded<T> {
  key: string
  state: AsyncState<T>
}

export function errorMessage(e: unknown, fallback: string): string {
  return e instanceof Error ? e.message : fallback
}

/**
 * key（ID など）が決まったら 1 回だけ load を呼び、結果を状態として返す。
 * key が変わるまで再取得しない。アンマウント後の setState はしない。
 */
export function useAsync<T>(
  key: string | undefined,
  load: (key: string) => Promise<T>,
  messages: { missingKey: string; failed: string },
): AsyncState<T> {
  const [loaded, setLoaded] = useState<Loaded<T> | null>(null)

  useEffect(() => {
    if (!key) return
    let cancelled = false
    load(key)
      .then((value) => {
        if (!cancelled) setLoaded({ key, state: { status: 'ready', value } })
      })
      .catch((e: unknown) => {
        if (!cancelled) {
          setLoaded({ key, state: { status: 'error', message: errorMessage(e, messages.failed) } })
        }
      })
    return () => {
      cancelled = true
    }
    // load / messages は呼び出し側で毎回新しく作られてもよいよう、key だけを見る
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key])

  if (!key) return { status: 'error', message: messages.missingKey }
  return loaded?.key === key ? loaded.state : { status: 'loading' }
}

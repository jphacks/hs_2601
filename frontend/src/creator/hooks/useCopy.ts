import { useEffect, useState } from 'react'

/** 「コピーしました」を出しておく時間（ms） */
const COPIED_RESET_MS = 2000

/** クリップボードへのコピー。最後にコピーしたキーを少しの間だけ返す */
export function useCopy() {
  const [copiedKey, setCopiedKey] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!copiedKey) return
    const timer = setTimeout(() => setCopiedKey(null), COPIED_RESET_MS)
    return () => clearTimeout(timer)
  }, [copiedKey])

  async function copy(key: string, text: string) {
    try {
      if (!navigator.clipboard) throw new Error('clipboard unavailable')
      await navigator.clipboard.writeText(text)
      setError(null)
      setCopiedKey(key)
    } catch {
      // http の LAN 接続などでは使えない。URL は画面に出ているので長押しでコピーしてもらう
      setError('コピーできませんでした。URL を長押ししてコピーしてください')
    }
  }

  return { copiedKey, error, copy }
}

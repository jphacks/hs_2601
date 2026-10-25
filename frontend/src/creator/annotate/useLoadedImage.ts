import { useEffect, useState } from 'react'
import { loadImage, type LoadedImage } from './exportImage'

type LoadState =
  | { source: Blob; image: LoadedImage; error: null }
  | { source: Blob; image: null; error: string }

/** 写真を読み込む。source が変わったら読み直し、不要になった画像は解放する */
export function useLoadedImage(source: Blob) {
  const [state, setState] = useState<LoadState | null>(null)

  useEffect(() => {
    let cancelled = false
    let loaded: LoadedImage | null = null
    loadImage(source).then(
      (image) => {
        if (cancelled) {
          image.close()
          return
        }
        loaded = image
        setState({ source, image, error: null })
      },
      (err: unknown) => {
        if (cancelled) return
        const message = err instanceof Error ? err.message : '写真を読み込めませんでした'
        setState({ source, image: null, error: message })
      },
    )
    return () => {
      cancelled = true
      loaded?.close()
    }
  }, [source])

  // 前の source の結果は使わない（読み込み中として扱う）
  const current = state?.source === source ? state : null
  return {
    loading: current === null,
    image: current?.image ?? null,
    error: current?.error ?? null,
  }
}

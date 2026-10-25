/** 開発用プレビュー画面。ルーターに触れずに PhotoAnnotator を確認する */
import { useEffect, useRef, useState } from 'react'
import { buttonClass } from '../components/styles'
import { PhotoAnnotator, type AnnotationResult } from './index'

interface Shown {
  result: AnnotationResult
  url: string
}

export function PreviewApp() {
  const [source, setSource] = useState<File | null>(null)
  const [editing, setEditing] = useState(false)
  const [shown, setShown] = useState<Shown | null>(null)
  const urlRef = useRef<string | null>(null)

  useEffect(() => () => {
    if (urlRef.current) URL.revokeObjectURL(urlRef.current)
  }, [])

  function show(result: AnnotationResult | null) {
    if (urlRef.current) URL.revokeObjectURL(urlRef.current)
    const url = result ? URL.createObjectURL(result.blob) : null
    urlRef.current = url
    setShown(result && url ? { result, url } : null)
  }

  return (
    <main className="mx-auto max-w-md space-y-4 p-4">
      <h1 className="text-lg font-bold">写真注釈プレビュー</h1>
      <input
        type="file"
        accept="image/*"
        capture="environment"
        onChange={(e) => {
          const file = e.target.files?.[0]
          if (!file) return
          setSource(file)
          show(null)
          setEditing(true)
          e.target.value = ''
        }}
      />
      {source && !editing && (
        <button className={buttonClass} onClick={() => setEditing(true)}>
          もう一度編集する（元の写真から）
        </button>
      )}
      {shown && (
        <section className="space-y-2">
          <img src={shown.url} alt="書き出し結果" className="w-full rounded-xl border" />
          <p className="text-sm">メッセージ: {shown.result.caption ?? '（なし）'}</p>
          <p className="text-sm text-stone-500">
            描画: {shown.result.drawn ? 'あり' : 'なし'} / {Math.round(shown.result.blob.size / 1024)}{' '}
            KB / {shown.result.blob.type}
          </p>
        </section>
      )}
      {source && editing && (
        <PhotoAnnotator
          source={source}
          initialCaption={shown?.result.caption}
          onDone={(r) => {
            show(r)
            setEditing(false)
          }}
          onCancel={() => setEditing(false)}
        />
      )}
    </main>
  )
}

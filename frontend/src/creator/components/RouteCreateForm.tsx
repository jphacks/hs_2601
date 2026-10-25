import { useRef } from 'react'
import type { CapturedPhoto } from '../types'
import { PhotoGrid } from './PhotoGrid'
import { buttonClass, inputClass, secondaryClass } from './styles'

interface Props {
  origin: string
  destination: string
  photos: CapturedPhoto[]
  /** 検証・通信エラー。なければ null */
  error: string | null
  submitting: boolean
  onOriginChange: (value: string) => void
  onDestinationChange: (value: string) => void
  onAddPhotos: (files: FileList | null) => void
  onRemovePhoto: (photo: CapturedPhoto) => void
  onSubmit: () => void
  onCancel: () => void
}

/** 「道を作る」画面。出発地・目的地の入力と目印写真の追加 */
export function RouteCreateForm({
  origin,
  destination,
  photos,
  error,
  submitting,
  onOriginChange,
  onDestinationChange,
  onAddPhotos,
  onRemovePhoto,
  onSubmit,
  onCancel,
}: Props) {
  const fileRef = useRef<HTMLInputElement>(null)

  function handleFiles(files: FileList | null) {
    onAddPhotos(files)
    if (fileRef.current) fileRef.current.value = ''
  }

  return (
    <section className="space-y-5">
      <h1 className="text-2xl font-bold">道を作る</h1>
      <label className="block space-y-2">
        <span className="text-sm font-semibold">出発地</span>
        <input
          className={inputClass}
          value={origin}
          onChange={(e) => onOriginChange(e.target.value)}
          placeholder="例：広島駅"
        />
      </label>
      <label className="block space-y-2">
        <span className="text-sm font-semibold">目的地</span>
        <input
          className={inputClass}
          value={destination}
          onChange={(e) => onDestinationChange(e.target.value)}
          placeholder="例：平和記念公園"
        />
      </label>

      <div className="space-y-3 rounded-2xl border border-stone-200 bg-white p-4">
        <div>
          <h2 className="font-bold">目印の写真</h2>
          <p className="mt-1 text-sm text-stone-500">
            曲がり角や入口など、迷いやすい場所を撮影してください。
          </p>
        </div>

        <input
          ref={fileRef}
          type="file"
          accept="image/*"
          capture="environment"
          multiple
          className="hidden"
          onChange={(e) => handleFiles(e.target.files)}
        />

        <button className={buttonClass} onClick={() => fileRef.current?.click()}>
          📷 写真を撮る・追加する
        </button>

        <PhotoGrid photos={photos} onRemove={onRemovePhoto} />
      </div>

      {error && (
        <p role="alert" className="rounded-xl bg-red-50 px-4 py-3 text-sm text-red-700">
          {error}
        </p>
      )}

      <button className={`${buttonClass} disabled:opacity-50`} disabled={submitting} onClick={onSubmit}>
        {submitting ? '送信中...' : '道案内を作成する'}
      </button>
      <button className={secondaryClass} onClick={onCancel}>
        キャンセル
      </button>
    </section>
  )
}

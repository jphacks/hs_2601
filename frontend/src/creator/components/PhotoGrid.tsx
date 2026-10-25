import { locationLabel, photoLocationStatus } from '../photoLocation'
import type { CapturedPhoto, PhotoLocationStatus } from '../types'

interface Props {
  photos: CapturedPhoto[]
  onRemove: (photo: CapturedPhoto) => void
  onRetryLocation: (photo: CapturedPhoto) => void
  /** 描画・メッセージ画面を開く */
  onAnnotate: (photo: CapturedPhoto) => void
}

const STATUS_CLASS: Record<PhotoLocationStatus['kind'], string> = {
  ok: 'text-emerald-700',
  acquiring: 'text-stone-500',
  failed: 'text-red-700',
}

/** 作成画面の目印写真サムネイル一覧。位置情報の状態と、取れなかったときの取り直しボタンを出す */
export function PhotoGrid({ photos, onRemove, onRetryLocation, onAnnotate }: Props) {
  if (photos.length === 0) {
    return (
      <div className="rounded-xl bg-stone-50 p-6 text-center text-sm text-stone-500">
        まだ写真がありません
      </div>
    )
  }

  return (
    <div className="grid grid-cols-2 gap-3">
      {photos.map((photo, index) => {
        const status = photoLocationStatus(photo)
        return (
          <div
            key={photo.id}
            className={`overflow-hidden rounded-xl border ${status.kind === 'failed' ? 'border-red-300' : ''}`}
          >
            <button
              type="button"
              className="block w-full"
              aria-label={`目印 ${index + 1} に描く・メッセージを付ける`}
              onClick={() => onAnnotate(photo)}
            >
              <img src={photo.preview} alt={`目印 ${index + 1}`} className="h-36 w-full object-cover" />
            </button>
            <div className="p-2">
              <p className="text-xs font-medium">目印 {index + 1}</p>
              <p className={`mt-1 text-xs ${STATUS_CLASS[status.kind]}`}>{locationLabel(status)}</p>
              {photo.caption && (
                <p className="mt-1 text-xs break-all text-stone-700">💬 {photo.caption}</p>
              )}
              <div className="mt-2 flex flex-wrap gap-x-3 gap-y-1">
                <button className="text-sm text-emerald-700" onClick={() => onAnnotate(photo)}>
                  {photo.annotated || photo.caption ? '描画・メッセージを編集' : '描く・メッセージ'}
                </button>
                {status.kind === 'failed' && (
                  <button className="text-sm text-emerald-700" onClick={() => onRetryLocation(photo)}>
                    位置を取り直す
                  </button>
                )}
                <button className="text-sm text-red-600" onClick={() => onRemove(photo)}>
                  削除
                </button>
              </div>
            </div>
          </div>
        )
      })}
    </div>
  )
}

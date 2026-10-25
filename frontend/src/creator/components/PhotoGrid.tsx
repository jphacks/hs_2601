import type { CapturedPhoto } from '../types'

interface Props {
  photos: CapturedPhoto[]
  onRemove: (photo: CapturedPhoto) => void
}

function locationLabel(photo: CapturedPhoto): string {
  if (photo.lat !== undefined) return '位置情報取得済み'
  if (photo.locationError) return `位置情報未取得（${photo.locationError}）`
  return '位置情報を取得中...'
}

/** 作成画面の目印写真サムネイル一覧 */
export function PhotoGrid({ photos, onRemove }: Props) {
  if (photos.length === 0) {
    return (
      <div className="rounded-xl bg-stone-50 p-6 text-center text-sm text-stone-500">
        まだ写真がありません
      </div>
    )
  }

  return (
    <div className="grid grid-cols-2 gap-3">
      {photos.map((photo, index) => (
        <div key={photo.id} className="overflow-hidden rounded-xl border">
          <img
            src={photo.preview}
            alt={`目印 ${index + 1}`}
            className="h-36 w-full object-cover"
          />
          <div className="p-2">
            <p className="text-xs font-medium">目印 {index + 1}</p>
            <p className="mt-1 text-xs text-stone-500">{locationLabel(photo)}</p>
            <button className="mt-2 text-sm text-red-600" onClick={() => onRemove(photo)}>
              削除
            </button>
          </div>
        </div>
      ))}
    </div>
  )
}

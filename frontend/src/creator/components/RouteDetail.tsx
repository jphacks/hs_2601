import type { Photo, Route } from '../types'
import { buttonClass, secondaryClass } from './styles'

interface Props {
  route: Route
  photos: Photo[]
  onPublish: () => void
  onEdit: () => void
}

/** 作成した道案内の確認画面 */
export function RouteDetail({ route, photos, onPublish, onEdit }: Props) {
  return (
    <section className="space-y-5">
      <h1 className="text-2xl font-bold">道案内の確認</h1>
      <div className="rounded-2xl border bg-white p-4">
        <p className="text-sm text-stone-500">出発地</p>
        <p className="font-semibold">{route.start}</p>
        <p className="my-2 text-emerald-700">↓</p>
        <p className="text-sm text-stone-500">目的地</p>
        <p className="font-semibold">{route.goal}</p>
      </div>
      <div className="space-y-3">
        {photos.map((photo, i) => (
          <div key={photo.id} className="overflow-hidden rounded-xl border bg-white">
            <img
              src={photo.preview}
              alt={`経路の写真 ${i + 1}`}
              className="h-52 w-full object-cover"
            />
            <div className="p-3">
              <p className="font-semibold">目印 {i + 1}</p>
              <p className="mt-1 text-sm text-stone-500">
                曲がる方向・距離の案内は、経路 API の接続後に表示します。
              </p>
            </div>
          </div>
        ))}
      </div>
      <button className={buttonClass} onClick={onPublish}>
        公開画面へ
      </button>
      <button className={secondaryClass} onClick={onEdit}>
        写真を追加・修正する
      </button>
    </section>
  )
}

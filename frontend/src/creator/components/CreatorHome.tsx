import { buttonClass, secondaryClass } from './styles'

interface Props {
  onCreate: () => void
  onRoutes: () => void
}

/** ホーム画面。「道を作る」「作った道を公開する」の入口 */
export function CreatorHome({ onCreate, onRoutes }: Props) {
  return (
    <section className="space-y-4">
      <h1 className="text-3xl font-bold">道案内をつくろう</h1>
      <p className="text-sm leading-6 text-stone-600">
        迷いやすい場所を写真に撮って、誰でも歩ける道案内を作ります。
      </p>
      <button onClick={onCreate} className={`${buttonClass} py-6 text-left`}>
        <span className="block text-2xl">📷</span>
        <span className="mt-3 block text-xl">道を作る</span>
        <span className="mt-1 block text-sm font-normal">
          出発地・目的地・目印の写真を登録
        </span>
      </button>
      <button onClick={onRoutes} className={`${secondaryClass} py-6 text-left`}>
        <span className="block text-2xl">🔗</span>
        <span className="mt-3 block text-xl">作った道を公開する</span>
        <span className="mt-1 block text-sm text-stone-500">
          作成済みの道を選んで共有
        </span>
      </button>
    </section>
  )
}

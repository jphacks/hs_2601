/** 道案内の作成中に表示するスピナー画面 */
export function RouteLoading() {
  return (
    <section className="py-20 text-center">
      <div className="mx-auto mb-5 h-10 w-10 animate-spin rounded-full border-4 border-stone-200 border-t-emerald-700" />
      <h1 className="text-xl font-bold">道案内を作成中...</h1>
      <p className="mt-3 text-sm text-stone-500">
        経路と写真を整理しています。
      </p>
    </section>
  )
}

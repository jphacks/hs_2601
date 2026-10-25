import { JOB_STEP_LABEL, JOB_STEPS } from '../../shared/lib/constants'
import type { JobStep } from '../../shared/types/creator'

interface Props {
  /** 今の処理段階。分からないときは null（作成中以外の読み込みでも null） */
  step?: JobStep | null
}

/** 道案内の作成中・読み込み中に表示するスピナー画面 */
export function RouteLoading({ step = null }: Props) {
  return (
    <section className="py-20 text-center">
      <div className="mx-auto mb-5 h-10 w-10 animate-spin rounded-full border-4 border-stone-200 border-t-emerald-700" />
      <h1 className="text-xl font-bold">道案内を作成中...</h1>
      <p className="mt-3 text-sm text-stone-500" aria-live="polite">
        {step ? `${JOB_STEP_LABEL[step]}...` : '経路と写真を整理しています。'}
      </p>
      {step && (
        <p className="mt-1 text-xs text-stone-400">
          {JOB_STEPS.indexOf(step) + 1} / {JOB_STEPS.length}
        </p>
      )}
    </section>
  )
}

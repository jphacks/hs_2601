import { useState } from 'react'
import type { RoutePlan } from '../types/routePlan'
import { StepView } from './StepView'

interface Props {
  plan: RoutePlan
  /** 外から現在ステップを制御するとき（位置追跡など）。省略時は内部で持つ */
  current?: number
  onCurrentChange?: (index: number) => void
}

const navButtonClass = 'flex-1 rounded-[14px] px-2.5 py-4 text-base font-bold'

/** 写真列全体の表示。進捗バーと「前へ」「次へ」を持つ。作る人の確認画面と参加者画面で共用 */
export function RoutePlanViewer({ plan, current, onCurrentChange }: Props) {
  const [internal, setInternal] = useState(0)
  const index = current ?? internal
  const total = plan.steps.length
  const step = plan.steps[index]
  const arrived = index >= total - 1
  const progress = total === 0 ? 0 : ((index + 1) / total) * 100

  function move(next: number) {
    const clamped = Math.max(0, Math.min(total - 1, next))
    setInternal(clamped)
    onCurrentChange?.(clamped)
  }

  if (!step) {
    return <p className="text-sm text-muted">この道案内にはステップがありません。</p>
  }

  return (
    <div>
      <div className="mt-[18px] h-[5px] overflow-hidden rounded-[10px] bg-track">
        <div
          className="h-full bg-brand transition-[width] duration-200"
          style={{ width: `${progress}%` }}
        />
      </div>
      <p className="mt-[7px] mb-6 text-right text-xs text-muted">
        {arrived ? 'すべての案内が完了しました' : `${index + 1} / ${total} ステップ`}
      </p>

      <StepView step={step} stepNumber={index + 1} />

      <div className="mt-[18px] flex gap-3">
        <button
          onClick={() => move(index - 1)}
          disabled={index === 0}
          className={`${navButtonClass} border border-line-strong bg-white text-brand disabled:cursor-not-allowed disabled:opacity-40`}
        >
          ← 前へ
        </button>
        <button
          onClick={() => move(index + 1)}
          disabled={arrived}
          className={`${navButtonClass} bg-brand text-white disabled:cursor-not-allowed disabled:opacity-50`}
        >
          {arrived ? '到着済み ✓' : '次へ →'}
        </button>
      </div>
    </div>
  )
}

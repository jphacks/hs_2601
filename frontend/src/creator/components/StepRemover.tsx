import type { RoutePlanRecord } from '../../shared/types/routePlan'
import { useStepRemoval } from '../hooks/useStepRemoval'
import { secondaryClass } from './styles'

interface Props {
  record: RoutePlanRecord
  /** 外した後の行（画面の写真列を差し替える） */
  onRemoved: (record: RoutePlanRecord) => void
}

/** 写真列から、要らない写真を選んで外す。ゴールの写真は外せない。公開中なら参加者の画面からも消える */
export function StepRemover({ record, onRemoved }: Props) {
  const removal = useStepRemoval(record)
  const steps = record.plan.steps
  const goal = steps.length - 1
  const count = removal.selected.size

  async function handleRemove() {
    const published = record.status === 'published' ? '公開中なので、参加者の画面からもすぐに消えます。' : ''
    if (!window.confirm(`選んだ ${count} 枚の写真を道案内から外します。${published}よろしいですか？`)) return
    const updated = await removal.remove()
    if (updated) onRemoved(updated)
  }

  return (
    <div className="space-y-3 rounded-2xl border bg-white p-4">
      <div>
        <h2 className="font-bold">写真を外す</h2>
        <p className="mt-1 text-sm text-stone-500">
          要らない写真を選んで外せます。外した地点までの距離は、1 つ前の写真に足されます。ゴールの写真は外せません。
        </p>
      </div>
      <ul className="grid grid-cols-3 gap-2">
        {steps.map((step, i) => {
          const isGoal = i === goal
          const checked = removal.selected.has(i)
          return (
            <li key={`${i}-${step.image_url ?? 'none'}`}>
              <label
                className={`block overflow-hidden rounded-xl border-2 ${checked ? 'border-red-500' : 'border-transparent'} ${isGoal ? 'opacity-50' : 'cursor-pointer'}`}
              >
                {step.image_url ? (
                  <img src={step.image_url} alt={`写真 ${i + 1}`} className="h-20 w-full object-cover" />
                ) : (
                  <div className="flex h-20 items-center justify-center bg-stone-100 text-xs text-stone-500">地点 {i + 1}</div>
                )}
                <span className="flex items-center gap-1 px-1 py-1 text-xs">
                  <input
                    type="checkbox"
                    checked={checked}
                    disabled={isGoal || removal.busy}
                    onChange={() => removal.toggle(i)}
                    aria-label={isGoal ? 'ゴールの写真は外せません' : `写真 ${i + 1} を外す`}
                  />
                  {isGoal ? 'ゴール' : `${i + 1}`}
                </span>
              </label>
            </li>
          )
        })}
      </ul>
      {removal.error && (
        <p role="alert" className="rounded-xl bg-red-50 px-4 py-3 text-sm text-red-700">
          {removal.error}
        </p>
      )}
      <button
        className={`${secondaryClass} border-red-300 text-red-700 disabled:opacity-50`}
        disabled={count === 0 || removal.busy}
        onClick={handleRemove}
      >
        {removal.busy ? '外しています...' : count === 0 ? '外す写真を選んでください' : `選んだ ${count} 枚を外す`}
      </button>
    </div>
  )
}

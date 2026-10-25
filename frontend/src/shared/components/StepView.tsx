import { TURN_ARROW, TURN_LABEL } from '../lib/constants'
import type { RouteStep } from '../types/routePlan'

interface Props {
  step: RouteStep
  /** 1 から始まる表示用の番号 */
  stepNumber: number
}

/** 1 ステップの表示（写真 + 矢印 + 目印文 + 次までの距離）。作る人の確認画面と参加者画面で共用 */
export function StepView({ step, stepNumber }: Props) {
  const arrived = step.turn === 'arrive'
  const description = step.landmark ?? step.instruction
  // 作成者の写真は写真とメッセージだけを見せる（左折・右折の表示は出さない。ゴールは出す）
  const showTurn = !step.creator_photo || arrived

  return (
    <section className="rounded-[20px] bg-white p-3 shadow-[0_4px_18px_#17291a0d]">
      <div className="relative overflow-hidden rounded-[14px] bg-photo-bg">
        {step.image_url ? (
          <img
            src={step.image_url}
            alt={`目印 ${stepNumber} の写真`}
            className="block h-[250px] w-full object-cover"
          />
        ) : (
          <div className="flex h-[250px] items-center justify-center text-sm text-muted">
            この地点の写真はありません
          </div>
        )}
        <span className="absolute top-3 left-3 rounded-lg bg-white/95 px-2.5 py-[7px] text-xs font-bold">
          {arrived ? 'GOAL' : `目印 ${stepNumber}`}
        </span>
      </div>

      <div className="flex items-center gap-3.5 px-2 py-[22px]">
        {showTurn && (
          <div className="flex h-[82px] w-[82px] shrink-0 items-center justify-center rounded-[20px] bg-brand text-5xl font-bold text-white">
            {TURN_ARROW[step.turn]}
          </div>
        )}
        <div>
          {showTurn && <h2 className="m-0 text-[25px] leading-[1.3] text-brand">{TURN_LABEL[step.turn]}</h2>}
          <p className={`${showTurn ? 'mt-2' : 'mt-0 text-base'} mb-0 text-sm leading-[1.8] text-ink-soft`}>{description}</p>
        </div>
      </div>

      <div className="flex items-center gap-3 border-t border-line px-2 pt-4 pb-2.5">
        <div className="text-[26px]">🚶</div>
        <div>
          <div className="text-xs text-muted">{arrived ? '目的地' : '次の目印まで'}</div>
          <div className="mt-[3px] text-[25px] font-extrabold">
            {arrived ? '到着！' : `約 ${step.distance_to_next_m} m`}
          </div>
        </div>
      </div>
    </section>
  )
}

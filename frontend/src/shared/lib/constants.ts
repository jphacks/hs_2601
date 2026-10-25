/** フロント全体で使う定数 */
import type { Turn } from '../types/routePlan'

/** 曲がる方向の表示文 */
export const TURN_LABEL: Record<Turn, string> = {
  left: '左に曲がる',
  right: '右に曲がる',
  straight: '直進',
  arrive: '到着！',
}

/** 曲がる方向の矢印記号 */
export const TURN_ARROW: Record<Turn, string> = {
  left: '↖',
  right: '↗',
  straight: '↑',
  arrive: '✓',
}

/** 作成ジョブのステータスを問い合わせる間隔（ms） */
export const JOB_POLL_INTERVAL_MS = 2000

/** fixture モードで作成完了とみなすまでの疑似待ち時間（ms） */
export const FIXTURE_CREATE_DELAY_MS = 1000

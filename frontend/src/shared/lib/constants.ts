/** フロント全体で使う定数 */
import type { JobStep } from '../types/creator'
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

/** 作成ジョブの処理段階（バックエンドが進める順） */
export const JOB_STEPS: readonly JobStep[] = ['geocode', 'route', 'streetview', 'landmark', 'arrow', 'save']

/** 作成中画面に出す処理段階の表示文 */
export const JOB_STEP_LABEL: Record<JobStep, string> = {
  geocode: '出発地・目的地の場所を調べています',
  route: '経路を計算しています',
  streetview: '道の写真を集めています',
  landmark: '目印を探しています',
  arrow: '矢印を描いています',
  save: '保存しています',
}

/** 送信する写真の長辺（px）。バックエンドも同じ大きさに揃える（interface.md 4 章） */
export const PHOTO_MAX_EDGE_PX = 1280

/** 送信する写真の JPEG 品質 */
export const PHOTO_JPEG_QUALITY = 0.88

/** 目的地を省略したときのゴールの呼び名（backend の GOAL_PHOTO_LABEL と同じ）。最後の写真がゴールになる */
export const GOAL_PHOTO_LABEL = '最後の写真の地点'

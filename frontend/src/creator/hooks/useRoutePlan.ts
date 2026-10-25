import { routeApi } from '../../shared/api/endpoints'
import { useAsync } from '../../shared/hooks/useAsync'

const MESSAGES = {
  missingKey: '道案内の ID が指定されていません',
  failed: '道案内を取得できませんでした',
}

/** 作成結果（下書き含む）の写真列を取得する。確認画面と詳細表示で使う */
export function useRoutePlan(routeId: string | undefined) {
  return useAsync(routeId, (id) => routeApi.getRoutePlan(id), MESSAGES)
}

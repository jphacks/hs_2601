import { routeApi } from '../../shared/api/endpoints'
import { useAsync } from '../../shared/hooks/useAsync'

const MESSAGES = {
  missingKey: '道案内の ID が指定されていません',
  failed: '道案内を取得できませんでした',
}

/** 公開済みの写真列 JSON を画面を開いたときに 1 回だけ取得する */
export function useRoutePlan(routeId: string | undefined) {
  return useAsync(routeId, (id) => routeApi.getPublicRoutePlan(id), MESSAGES)
}

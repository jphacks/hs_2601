/** 写真の位置情報まわりの純粋関数。useCapture・PhotoGrid・入力検証で使う */
import type { CapturedPhoto, PhotoLocationStatus } from './types'

/** GeolocationPositionError.code（1: 拒否、2: 取得不可、3: タイムアウト） */
const GEOLOCATION_ERROR: Record<number, string> = {
  1: '位置情報の利用が許可されていません',
  2: '現在地を取得できませんでした',
  3: '位置情報の取得に時間がかかりすぎました',
}

export function geolocationErrorMessage(code: number): string {
  return GEOLOCATION_ERROR[code] ?? '位置情報を取得できませんでした'
}

export function photoLocationStatus(photo: CapturedPhoto): PhotoLocationStatus {
  if (photo.lat !== undefined && photo.lng !== undefined) {
    return { kind: 'ok', lat: photo.lat, lng: photo.lng, accuracyM: photo.accuracyM }
  }
  if (photo.locationError) return { kind: 'failed', reason: photo.locationError }
  return { kind: 'acquiring' }
}

/** 一覧に出す短い表示。精度は m 単位に丸める */
export function locationLabel(status: PhotoLocationStatus): string {
  switch (status.kind) {
    case 'ok':
      return status.accuracyM === undefined
        ? '位置情報 OK'
        : `位置情報 OK（±${Math.round(status.accuracyM)}m）`
    case 'failed':
      return `位置情報なし（${status.reason}）`
    case 'acquiring':
      return '位置情報を取得中...'
  }
}

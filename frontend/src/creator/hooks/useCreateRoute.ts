import { useState } from 'react'
import { routeApi } from '../../shared/api/endpoints'
import { apiErrorMessage } from '../../shared/api/errors'
import { toIsoWithOffset } from '../../shared/lib/datetime'
import { toJpeg } from '../../shared/lib/image'
import type { CreateRouteInput, CreateRouteResult } from '../../shared/types/creator'
import { photoLocationStatus } from '../photoLocation'
import { getOrCreateCreatorId } from '../storage/creatorId'
import type { CapturedPhoto } from '../types'

export interface DraftInput {
  name: string
  origin: string
  destination: string
  photos: CapturedPhoto[]
}

/** 送信の段階。画面のボタン表示に使う */
export type SubmitPhase = 'idle' | 'converting' | 'uploading'

/** 写真の番号（目印 1, 2, ...）を「目印 1・3」の形にする */
function photoNumbers(photos: CapturedPhoto[], pick: (p: CapturedPhoto) => boolean): string {
  return photos
    .flatMap((p, i) => (pick(p) ? [`目印 ${i + 1}`] : []))
    .join('・')
}

/** 入力を検証し、問題があればエラー文を返す。なければ null */
export function validateDraft({ name, origin, destination, photos }: DraftInput): string | null {
  if (!name.trim()) return '道の名前を入力してください'
  if (!origin.trim() || !destination.trim()) return '出発地と目的地を入力してください'
  if (photos.length === 0) return '目印となる写真を撮影してください'

  const failed = photoNumbers(photos, (p) => photoLocationStatus(p).kind === 'failed')
  if (failed) return `${failed} の位置情報が取れていません。位置を取り直すか、写真を削除してください`
  const acquiring = photoNumbers(photos, (p) => photoLocationStatus(p).kind === 'acquiring')
  if (acquiring) return `${acquiring} の位置情報を取得中です。少し待ってからもう一度押してください`
  return null
}

/** 写真を 1 枚ずつ JPEG にする（スマホのメモリを考えて並列にしない）。失敗したらどの写真かを添えて投げる */
export async function convertPhotos(
  photos: CapturedPhoto[],
  convert: (file: File) => Promise<Blob>,
): Promise<Blob[]> {
  const jpegs: Blob[] = []
  for (const [i, photo] of photos.entries()) {
    try {
      jpegs.push(await convert(photo.file))
    } catch {
      throw new Error(
        `目印 ${i + 1} の写真を読み込めませんでした。別の形式で撮り直すか、写真を削除してください`,
      )
    }
  }
  return jpegs
}

/** 検証済みの入力と変換済み JPEG から作成受付の入力を作る。座標が無い写真があれば例外 */
export function buildCreateInput(
  draft: DraftInput,
  jpegs: Blob[],
  creatorId: string,
  createdAt: string,
): CreateRouteInput {
  if (jpegs.length !== draft.photos.length) throw new Error('写真の枚数が合いません')
  return {
    name: draft.name.trim(),
    origin: draft.origin.trim(),
    destination: draft.destination.trim(),
    creatorId,
    createdAt,
    photos: draft.photos.map((photo, i) => {
      const location = photoLocationStatus(photo)
      if (location.kind !== 'ok') throw new Error(`目印 ${i + 1} の位置情報がありません`)
      return {
        id: photo.id,
        file: jpegs[i],
        lat: location.lat,
        lng: location.lng,
        accuracyM: location.accuracyM,
        takenAt: photo.takenAt,
      }
    }),
  }
}

/** 入力を検証し、写真を JPEG にして作成受付 API を呼ぶ。検証エラーと通信エラーは state で返す */
export function useCreateRoute(onAccepted: (result: CreateRouteResult) => void) {
  const [error, setError] = useState<string | null>(null)
  const [phase, setPhase] = useState<SubmitPhase>('idle')

  async function submit(draft: DraftInput) {
    if (phase !== 'idle') return
    const validation = validateDraft(draft)
    if (validation) {
      setError(validation)
      return
    }
    setError(null)
    try {
      setPhase('converting')
      const jpegs = await convertPhotos(draft.photos, (file) => toJpeg(file))
      setPhase('uploading')
      const input = buildCreateInput(draft, jpegs, getOrCreateCreatorId(), toIsoWithOffset(new Date()))
      onAccepted(await routeApi.createRoute(input))
    } catch (e) {
      setError(apiErrorMessage(e, '作成を受け付けられませんでした'))
    } finally {
      setPhase('idle')
    }
  }

  return { error, phase, submitting: phase !== 'idle', submit }
}

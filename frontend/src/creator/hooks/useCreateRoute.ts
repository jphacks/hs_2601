import { useState } from 'react'
import { routeApi } from '../../shared/api/endpoints'
import { getOrCreateCreatorId } from '../storage/creatorId'
import type { CapturedPhoto } from '../types'

interface DraftInput {
  origin: string
  destination: string
  photos: CapturedPhoto[]
}

/** 入力を検証し、問題があればエラー文を返す。なければ null */
export function validateDraft({ origin, destination, photos }: DraftInput): string | null {
  if (!origin.trim() || !destination.trim()) return '出発地と目的地を入力してください'
  if (photos.length === 0) return '目印となる写真を撮影してください'
  return null
}

/** 作成受付 API を呼び、ジョブ ID を返す。検証エラーと通信エラーは state で返す */
export function useCreateRoute(onAccepted: (jobId: string) => void) {
  const [error, setError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)

  async function submit(draft: DraftInput) {
    const validation = validateDraft(draft)
    if (validation) {
      setError(validation)
      return
    }
    setError(null)
    setSubmitting(true)
    try {
      const { jobId } = await routeApi.createRoute({
        origin: draft.origin.trim(),
        destination: draft.destination.trim(),
        photos: draft.photos.map(({ file, lat, lng }) => ({ file, lat, lng })),
        creatorId: getOrCreateCreatorId(),
      })
      onAccepted(jobId)
    } catch (e) {
      setError(e instanceof Error ? e.message : '作成を受け付けられませんでした')
    } finally {
      setSubmitting(false)
    }
  }

  return { error, submitting, submit }
}

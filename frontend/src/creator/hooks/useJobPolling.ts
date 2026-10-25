import { useEffect, useState } from 'react'
import { routeApi } from '../../shared/api/endpoints'
import { apiErrorMessage } from '../../shared/api/errors'
import { JOB_POLL_INTERVAL_MS } from '../../shared/lib/constants'
import type { JobStatus, JobStep } from '../../shared/types/creator'

export type PollingState =
  | { status: 'running'; step: JobStep | null }
  | { status: 'done'; routeId: string }
  | { status: 'failed'; message: string }

interface Polled {
  jobId: string
  state: PollingState
}

/** ステータス API の返りを画面の状態にする */
export function toPollingState(job: JobStatus): PollingState {
  if (job.state === 'done') {
    return job.routeId
      ? { status: 'done', routeId: job.routeId }
      : { status: 'failed', message: '作成結果の ID が返ってきませんでした' }
  }
  if (job.state === 'failed') return { status: 'failed', message: job.message || '作成に失敗しました' }
  return { status: 'running', step: job.step ?? null }
}

/** ステータス API を数秒おきに叩き、完了か失敗で止める。ページを離れたら止まる */
export function useJobPolling(jobId: string | undefined): PollingState {
  const [polled, setPolled] = useState<Polled | null>(null)

  useEffect(() => {
    if (!jobId) return
    const id = jobId
    let cancelled = false
    let timer: ReturnType<typeof setTimeout> | undefined

    async function tick() {
      let next: PollingState
      try {
        next = toPollingState(await routeApi.getJobStatus(id))
      } catch (e) {
        next = { status: 'failed', message: apiErrorMessage(e, '状態を取得できませんでした') }
      }
      if (cancelled) return
      setPolled({ jobId: id, state: next })
      if (next.status === 'running') timer = setTimeout(tick, JOB_POLL_INTERVAL_MS)
    }

    tick()
    return () => {
      cancelled = true
      if (timer) clearTimeout(timer)
    }
  }, [jobId])

  if (!jobId) return { status: 'failed', message: 'ジョブ ID が指定されていません' }
  return polled?.jobId === jobId ? polled.state : { status: 'running', step: null }
}

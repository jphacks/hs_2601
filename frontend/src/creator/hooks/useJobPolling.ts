import { useEffect, useState } from 'react'
import { routeApi } from '../../shared/api/endpoints'
import { errorMessage } from '../../shared/hooks/useAsync'
import { JOB_POLL_INTERVAL_MS } from '../../shared/lib/constants'
import type { JobStatus } from '../../shared/types/creator'

export type PollingState =
  | { status: 'running' }
  | { status: 'done'; routeId: string }
  | { status: 'failed'; message: string }

interface Finished {
  jobId: string
  state: PollingState
}

/** 終わっていれば done / failed、まだなら null */
function finishedState(job: JobStatus): PollingState | null {
  if (job.state === 'done' && job.routeId) return { status: 'done', routeId: job.routeId }
  if (job.state === 'failed') return { status: 'failed', message: job.message ?? '作成に失敗しました' }
  return null
}

/** ステータス API を数秒おきに叩き、完了か失敗で止める。ページを離れたら止まる */
export function useJobPolling(jobId: string | undefined): PollingState {
  const [finished, setFinished] = useState<Finished | null>(null)

  useEffect(() => {
    if (!jobId) return
    const id = jobId
    let cancelled = false
    let timer: ReturnType<typeof setTimeout> | undefined

    async function tick() {
      let next: PollingState | null
      try {
        next = finishedState(await routeApi.getJobStatus(id))
      } catch (e) {
        next = { status: 'failed', message: errorMessage(e, '状態を取得できませんでした') }
      }
      if (cancelled) return
      if (next) {
        setFinished({ jobId: id, state: next })
        return
      }
      timer = setTimeout(tick, JOB_POLL_INTERVAL_MS)
    }

    tick()
    return () => {
      cancelled = true
      if (timer) clearTimeout(timer)
    }
  }, [jobId])

  if (!jobId) return { status: 'failed', message: 'ジョブ ID が指定されていません' }
  return finished?.jobId === jobId ? finished.state : { status: 'running' }
}

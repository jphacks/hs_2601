import { describe, expect, it } from 'vitest'
import { toPollingState } from './useJobPolling'

describe('toPollingState', () => {
  it('running は step を引き継ぐ（無ければ null）', () => {
    expect(toPollingState({ jobId: 'j', state: 'running', step: 'route' })).toEqual({ status: 'running', step: 'route' })
    expect(toPollingState({ jobId: 'j', state: 'running' })).toEqual({ status: 'running', step: null })
  })

  it('done は routeId、無ければ失敗扱い', () => {
    expect(toPollingState({ jobId: 'j', state: 'done', routeId: 'r1' })).toEqual({ status: 'done', routeId: 'r1' })
    expect(toPollingState({ jobId: 'j', state: 'done', routeId: null }).status).toBe('failed')
  })

  it('failed は message、無ければ既定文', () => {
    expect(toPollingState({ jobId: 'j', state: 'failed', message: '経路が見つかりません' })).toEqual({
      status: 'failed',
      message: '経路が見つかりません',
    })
    expect(toPollingState({ jobId: 'j', state: 'failed', message: null })).toEqual({
      status: 'failed',
      message: '作成に失敗しました',
    })
  })
})

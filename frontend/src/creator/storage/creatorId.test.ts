import { describe, expect, it } from 'vitest'
import { getOrCreateCreatorId } from './creatorId'

function memoryStorage(): Storage {
  const map = new Map<string, string>()
  return {
    get length() {
      return map.size
    },
    clear: () => map.clear(),
    getItem: (k) => map.get(k) ?? null,
    key: (i) => [...map.keys()][i] ?? null,
    removeItem: (k) => void map.delete(k),
    setItem: (k, v) => void map.set(k, v),
  }
}

describe('getOrCreateCreatorId', () => {
  it('初回は生成して保存し、2 回目以降は同じ ID を返す', () => {
    const storage = memoryStorage()
    const first = getOrCreateCreatorId(storage)
    expect(first).toMatch(/^[0-9a-f-]{36}$/)
    expect(getOrCreateCreatorId(storage)).toBe(first)
    expect(storage.length).toBe(1)
  })

  it('別のストレージなら別の ID になる', () => {
    expect(getOrCreateCreatorId(memoryStorage())).not.toBe(getOrCreateCreatorId(memoryStorage()))
  })
})

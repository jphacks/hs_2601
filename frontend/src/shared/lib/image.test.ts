import { describe, expect, it } from 'vitest'
import { fitWithin } from './image'

describe('fitWithin', () => {
  it('横長は横を 1280 に合わせ、縦横比を保つ', () => {
    expect(fitWithin({ width: 4032, height: 3024 }, 1280)).toEqual({ width: 1280, height: 960 })
  })

  it('縦長は縦を 1280 に合わせる', () => {
    expect(fitWithin({ width: 3024, height: 4032 }, 1280)).toEqual({ width: 960, height: 1280 })
  })

  it('小さい画像は拡大しない', () => {
    expect(fitWithin({ width: 800, height: 600 }, 1280)).toEqual({ width: 800, height: 600 })
    expect(fitWithin({ width: 1280, height: 1280 }, 1280)).toEqual({ width: 1280, height: 1280 })
  })

  it('端数は四捨五入し、極端に細長くても 1px 以上', () => {
    expect(fitWithin({ width: 3000, height: 2001 }, 1280)).toEqual({ width: 1280, height: 854 })
    expect(fitWithin({ width: 100000, height: 10 }, 1280)).toEqual({ width: 1280, height: 1 })
  })

  it('大きさが 0 以下なら例外', () => {
    expect(() => fitWithin({ width: 0, height: 100 }, 1280)).toThrow()
  })
})

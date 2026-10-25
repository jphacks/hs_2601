import { describe, expect, it } from 'vitest'
import {
  appendPoint,
  clientToImage,
  containSize,
  fitExportSize,
  hasDrawing,
  startStroke,
  strokeWidthFor,
  type Stroke,
} from './strokes'

describe('fitExportSize', () => {
  it('長辺を 1280 に縮小し縦横比を保つ', () => {
    expect(fitExportSize({ width: 4032, height: 3024 })).toEqual({ width: 1280, height: 960 })
    expect(fitExportSize({ width: 3024, height: 4032 })).toEqual({ width: 960, height: 1280 })
  })

  it('小さい画像は拡大しない', () => {
    expect(fitExportSize({ width: 800, height: 600 })).toEqual({ width: 800, height: 600 })
    expect(fitExportSize({ width: 1280, height: 720 })).toEqual({ width: 1280, height: 720 })
  })

  it('上限を指定できる・不正なサイズは 0', () => {
    expect(fitExportSize({ width: 2000, height: 1000 }, 500)).toEqual({ width: 500, height: 250 })
    expect(fitExportSize({ width: 0, height: 100 })).toEqual({ width: 0, height: 0 })
  })
})

describe('containSize', () => {
  it('縦長の写真は高さに合わせて収める', () => {
    expect(containSize({ width: 960, height: 1280 }, { width: 390, height: 400 })).toEqual({
      width: 300,
      height: 400,
    })
  })

  it('横長の写真は幅に合わせて収める', () => {
    expect(containSize({ width: 1280, height: 960 }, { width: 390, height: 600 })).toEqual({
      width: 390,
      height: 292,
    })
  })

  it('箱が未計測なら 0', () => {
    expect(containSize({ width: 100, height: 100 }, { width: 0, height: 0 })).toEqual({
      width: 0,
      height: 0,
    })
  })
})

describe('clientToImage', () => {
  const rect = { left: 10, top: 50, width: 300, height: 400 }
  const image = { width: 960, height: 1280 }

  it('表示座標を画像ピクセル座標に拡大して変換する', () => {
    expect(clientToImage({ x: 10, y: 50 }, rect, image)).toEqual({ x: 0, y: 0 })
    expect(clientToImage({ x: 160, y: 250 }, rect, image)).toEqual({ x: 480, y: 640 })
    expect(clientToImage({ x: 310, y: 450 }, rect, image)).toEqual({ x: 960, y: 1280 })
  })

  it('画像の外は端に丸める', () => {
    expect(clientToImage({ x: -100, y: 1000 }, rect, image)).toEqual({ x: 0, y: 1280 })
  })

  it('要素の大きさが 0 なら原点', () => {
    expect(clientToImage({ x: 5, y: 5 }, { ...rect, width: 0 }, image)).toEqual({ x: 0, y: 0 })
  })
})

describe('strokeWidthFor', () => {
  it('画像の長辺に比例し、消しゴムはペンより太い', () => {
    const big = strokeWidthFor('red', { width: 1280, height: 960 })
    const small = strokeWidthFor('red', { width: 640, height: 480 })
    expect(big).toBe(13)
    expect(small).toBe(6)
    expect(strokeWidthFor('eraser', { width: 1280, height: 960 })).toBe(big * 4)
  })

  it('極小画像でも最低 2px', () => {
    expect(strokeWidthFor('blue', { width: 50, height: 50 })).toBe(2)
  })
})

describe('stroke model', () => {
  const image = { width: 1000, height: 1000 }

  it('startStroke は道具と太さと最初の点を持つ', () => {
    const s = startStroke('blue', { x: 1, y: 2 }, image)
    expect(s).toEqual({ tool: 'blue', width: 10, points: [{ x: 1, y: 2 }] })
  })

  it('appendPoint は新しい線を返し、元の線を変更しない', () => {
    const s = startStroke('red', { x: 0, y: 0 }, image)
    const next = appendPoint(s, { x: 10, y: 0 })
    expect(next.points).toEqual([
      { x: 0, y: 0 },
      { x: 10, y: 0 },
    ])
    expect(s.points).toHaveLength(1)
  })

  it('近すぎる点は追加せず同じ線を返す', () => {
    const s = startStroke('red', { x: 0, y: 0 }, image)
    expect(appendPoint(s, { x: 0.5, y: 0.5 })).toBe(s)
  })

  it('hasDrawing はペンの線があるときだけ true（消しゴムだけなら false）', () => {
    const pen: Stroke = startStroke('red', { x: 0, y: 0 }, image)
    const eraser: Stroke = startStroke('eraser', { x: 0, y: 0 }, image)
    expect(hasDrawing([])).toBe(false)
    expect(hasDrawing([eraser])).toBe(false)
    expect(hasDrawing([pen, eraser])).toBe(true)
  })
})

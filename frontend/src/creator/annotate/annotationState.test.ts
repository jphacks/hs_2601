import { describe, expect, it } from 'vitest'
import { annotationReducer, initialAnnotationState } from './annotationState'
import { startStroke } from './strokes'

const image = { width: 100, height: 100 }
const pen = startStroke('red', { x: 1, y: 1 }, image)
const eraser = startStroke('eraser', { x: 1, y: 1 }, image)

describe('initialAnnotationState', () => {
  it('赤ペン・線なし・既存メッセージで始まる', () => {
    expect(initialAnnotationState('既存')).toEqual({ tool: 'red', strokes: [], caption: '既存' })
    expect(initialAnnotationState(null).caption).toBe('')
    expect(initialAnnotationState().caption).toBe('')
  })
})

describe('annotationReducer', () => {
  const base = initialAnnotationState()

  it('道具を切り替える', () => {
    expect(annotationReducer(base, { type: 'setTool', tool: 'eraser' }).tool).toBe('eraser')
  })

  it('線を順に追加し、元の state は変更しない', () => {
    const s1 = annotationReducer(base, { type: 'addStroke', stroke: pen })
    const s2 = annotationReducer(s1, { type: 'addStroke', stroke: eraser })
    expect(s2.strokes).toEqual([pen, eraser])
    expect(s1.strokes).toEqual([pen])
    expect(base.strokes).toEqual([])
  })

  it('点の無い線は無視する', () => {
    const empty = { ...pen, points: [] }
    expect(annotationReducer(base, { type: 'addStroke', stroke: empty })).toBe(base)
  })

  it('undo は最後の線だけ取り除く（消しゴムの線も 1 本として戻せる）', () => {
    const s = { ...base, strokes: [pen, eraser] }
    expect(annotationReducer(s, { type: 'undo' }).strokes).toEqual([pen])
    expect(annotationReducer(base, { type: 'undo' })).toBe(base)
  })

  it('clear は線をすべて消すがメッセージと道具は残す', () => {
    const s = { tool: 'blue' as const, strokes: [pen, eraser], caption: 'メモ' }
    expect(annotationReducer(s, { type: 'clear' })).toEqual({
      tool: 'blue',
      strokes: [],
      caption: 'メモ',
    })
  })

  it('メッセージは入力どおり保持する（整形は書き出し時）', () => {
    expect(annotationReducer(base, { type: 'setCaption', caption: ' 右へ\n' }).caption).toBe(' 右へ\n')
  })
})

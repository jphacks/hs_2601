/** 注釈画面の状態（道具・線・メッセージ）と reducer。React に依存しない */
import type { Stroke, Tool } from './strokes'

export interface AnnotationState {
  tool: Tool
  strokes: readonly Stroke[]
  caption: string
}

export type AnnotationAction =
  | { type: 'setTool'; tool: Tool }
  | { type: 'addStroke'; stroke: Stroke }
  | { type: 'undo' }
  | { type: 'clear' }
  | { type: 'setCaption'; caption: string }

export function initialAnnotationState(caption?: string | null): AnnotationState {
  return { tool: 'red', strokes: [], caption: caption ?? '' }
}

export function annotationReducer(
  state: AnnotationState,
  action: AnnotationAction,
): AnnotationState {
  switch (action.type) {
    case 'setTool':
      return { ...state, tool: action.tool }
    case 'addStroke':
      if (action.stroke.points.length === 0) return state
      return { ...state, strokes: [...state.strokes, action.stroke] }
    case 'undo':
      if (state.strokes.length === 0) return state
      return { ...state, strokes: state.strokes.slice(0, -1) }
    case 'clear':
      if (state.strokes.length === 0) return state
      return { ...state, strokes: [] }
    case 'setCaption':
      return { ...state, caption: action.caption }
  }
}

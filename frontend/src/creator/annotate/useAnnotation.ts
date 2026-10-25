import { useCallback, useMemo, useReducer } from 'react'
import { annotationReducer, initialAnnotationState } from './annotationState'
import { isCaptionTooLong } from './caption'
import { hasDrawing, type Stroke, type Tool } from './strokes'

/** 注釈画面の状態（道具・線・メッセージ）をまとめて扱う */
export function useAnnotation(initialCaption?: string | null) {
  const [state, dispatch] = useReducer(annotationReducer, initialCaption, initialAnnotationState)

  const setTool = useCallback((tool: Tool) => dispatch({ type: 'setTool', tool }), [])
  const addStroke = useCallback((stroke: Stroke) => dispatch({ type: 'addStroke', stroke }), [])
  const undo = useCallback(() => dispatch({ type: 'undo' }), [])
  const clear = useCallback(() => dispatch({ type: 'clear' }), [])
  const setCaption = useCallback(
    (caption: string) => dispatch({ type: 'setCaption', caption }),
    [],
  )

  const drawn = useMemo(() => hasDrawing(state.strokes), [state.strokes])
  const captionTooLong = isCaptionTooLong(state.caption)

  return { ...state, drawn, captionTooLong, setTool, addStroke, undo, clear, setCaption }
}

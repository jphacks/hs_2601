import { useEffect, useRef, useState, type PointerEvent as ReactPointerEvent } from 'react'
import { drawDot, drawSegment, renderPhoto, renderStrokes, type LoadedImage } from './exportImage'
import {
  appendPoint,
  clientToImage,
  containSize,
  startStroke,
  type Size,
  type Stroke,
  type Tool,
} from './strokes'

interface Props {
  image: LoadedImage
  /** キャンバスの画素サイズ（= 書き出しサイズ） */
  size: Size
  strokes: readonly Stroke[]
  tool: Tool
  onStrokeEnd: (stroke: Stroke) => void
}

/** 親要素の大きさを測る */
function useElementSize<T extends HTMLElement>() {
  const ref = useRef<T>(null)
  const [size, setSize] = useState<Size>({ width: 0, height: 0 })
  useEffect(() => {
    const el = ref.current
    if (!el) return
    const observer = new ResizeObserver(([entry]) => {
      if (!entry) return
      const { width, height } = entry.contentRect
      setSize({ width, height })
    })
    observer.observe(el)
    return () => observer.disconnect()
  }, [])
  return [ref, size] as const
}

/**
 * 写真キャンバスと線キャンバスを重ねた描画面。
 * 線は書き出しサイズの画素座標で持ち、表示は CSS で縮小するだけなので書き出し後もずれない。
 */
export function DrawingSurface({ image, size, strokes, tool, onStrokeEnd }: Props) {
  const [boxRef, boxSize] = useElementSize<HTMLDivElement>()
  const display = containSize(size, boxSize)
  const photoRef = useRef<HTMLCanvasElement>(null)
  const overlayRef = useRef<HTMLCanvasElement>(null)
  const drawingRef = useRef<{ pointerId: number; stroke: Stroke } | null>(null)

  useEffect(() => {
    const ctx = photoRef.current?.getContext('2d')
    if (ctx) renderPhoto(ctx, image)
  }, [image, size])

  useEffect(() => {
    const ctx = overlayRef.current?.getContext('2d')
    if (ctx) renderStrokes(ctx, strokes)
  }, [strokes, size])

  function toImagePoint(e: { clientX: number; clientY: number }) {
    const rect = overlayRef.current!.getBoundingClientRect()
    return clientToImage({ x: e.clientX, y: e.clientY }, rect, size)
  }

  function handlePointerDown(e: ReactPointerEvent<HTMLCanvasElement>) {
    if (drawingRef.current || !e.isPrimary || e.button !== 0) return
    const ctx = overlayRef.current?.getContext('2d')
    if (!ctx) return
    e.currentTarget.setPointerCapture(e.pointerId)
    const stroke = startStroke(tool, toImagePoint(e), size)
    drawDot(ctx, stroke, stroke.points[0]!)
    drawingRef.current = { pointerId: e.pointerId, stroke }
  }

  function handlePointerMove(e: ReactPointerEvent<HTMLCanvasElement>) {
    const drawing = drawingRef.current
    const ctx = overlayRef.current?.getContext('2d')
    if (!drawing || drawing.pointerId !== e.pointerId || !ctx) return
    // 速く動かしても線がカクつかないよう、間引かれたイベントも拾う
    const events = e.nativeEvent.getCoalescedEvents?.() ?? []
    const samples = events.length > 0 ? events : [e.nativeEvent]
    let stroke = drawing.stroke
    for (const sample of samples) {
      const next = appendPoint(stroke, toImagePoint(sample))
      if (next === stroke) continue
      const pts = next.points
      drawSegment(ctx, next, pts[pts.length - 2]!, pts[pts.length - 1]!)
      stroke = next
    }
    drawingRef.current = { ...drawing, stroke }
  }

  function handlePointerEnd(e: ReactPointerEvent<HTMLCanvasElement>) {
    const drawing = drawingRef.current
    if (!drawing || drawing.pointerId !== e.pointerId) return
    drawingRef.current = null
    onStrokeEnd(drawing.stroke)
  }

  return (
    <div ref={boxRef} className="flex h-full w-full items-center justify-center overflow-hidden">
      <div className="relative" style={{ width: display.width, height: display.height }}>
        <canvas
          ref={photoRef}
          width={size.width}
          height={size.height}
          className="absolute inset-0 h-full w-full"
        />
        <canvas
          ref={overlayRef}
          width={size.width}
          height={size.height}
          aria-label="写真の上に指で書き込めます"
          className="absolute inset-0 h-full w-full"
          style={{ touchAction: 'none' }}
          onPointerDown={handlePointerDown}
          onPointerMove={handlePointerMove}
          onPointerUp={handlePointerEnd}
          onPointerCancel={handlePointerEnd}
        />
      </div>
    </div>
  )
}

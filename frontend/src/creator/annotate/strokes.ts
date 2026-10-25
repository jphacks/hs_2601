/**
 * 描画（ストローク）のモデルと座標・サイズ計算。DOM に依存しない純粋関数だけを置く。
 * 座標はすべて「書き出し画像のピクセル座標」で持つ。表示サイズが変わっても線がずれない。
 */

/** 選べる道具 */
export type Tool = 'red' | 'blue' | 'eraser'

export interface Point {
  x: number
  y: number
}

export interface Size {
  width: number
  height: number
}

/** 1 本の線。eraser は描画レイヤーだけを destination-out で消す */
export interface Stroke {
  tool: Tool
  /** 線の太さ（画像ピクセル） */
  width: number
  points: readonly Point[]
}

/** 書き出し画像の長辺の上限 */
export const MAX_EXPORT_EDGE = 1280
/** JPEG 品質 */
export const JPEG_QUALITY = 0.88

/** ペンの色 */
export const PEN_COLORS: Readonly<Record<Exclude<Tool, 'eraser'>, string>> = {
  red: '#ef4444',
  blue: '#2563eb',
}

/** 長辺に対するペン幅の比率（どの解像度でも見た目の太さをそろえる） */
const PEN_WIDTH_RATIO = 0.01
/** 消しゴムはペンの何倍の太さか */
const ERASER_SCALE = 4
/** これより近い点は追加しない（画像ピクセル） */
const MIN_POINT_DISTANCE = 1.5

/** 長辺が maxEdge 以下になるよう縮小したサイズ（拡大はしない） */
export function fitExportSize(source: Size, maxEdge: number = MAX_EXPORT_EDGE): Size {
  const { width, height } = source
  if (width <= 0 || height <= 0) return { width: 0, height: 0 }
  const scale = Math.min(1, maxEdge / Math.max(width, height))
  return {
    width: Math.max(1, Math.round(width * scale)),
    height: Math.max(1, Math.round(height * scale)),
  }
}

/** 縦横比を保ったまま box に収まる最大サイズ（object-fit: contain 相当。拡大もする） */
export function containSize(image: Size, box: Size): Size {
  if (image.width <= 0 || image.height <= 0 || box.width <= 0 || box.height <= 0) {
    return { width: 0, height: 0 }
  }
  const scale = Math.min(box.width / image.width, box.height / image.height)
  return {
    width: Math.floor(image.width * scale),
    height: Math.floor(image.height * scale),
  }
}

/** 表示中の要素の位置（getBoundingClientRect の必要部分） */
export interface Rect {
  left: number
  top: number
  width: number
  height: number
}

/** 画面座標（clientX/Y）を画像ピクセル座標に変換する。画像の外は端に丸める */
export function clientToImage(client: Point, rect: Rect, image: Size): Point {
  if (rect.width <= 0 || rect.height <= 0) return { x: 0, y: 0 }
  const x = ((client.x - rect.left) / rect.width) * image.width
  const y = ((client.y - rect.top) / rect.height) * image.height
  return { x: clamp(x, 0, image.width), y: clamp(y, 0, image.height) }
}

/** 道具と画像サイズから線の太さを決める */
export function strokeWidthFor(tool: Tool, image: Size): number {
  const pen = Math.max(2, Math.round(Math.max(image.width, image.height) * PEN_WIDTH_RATIO))
  return tool === 'eraser' ? pen * ERASER_SCALE : pen
}

/** 新しい線を始める */
export function startStroke(tool: Tool, point: Point, image: Size): Stroke {
  return { tool, width: strokeWidthFor(tool, image), points: [point] }
}

/** 点を追加した新しい線を返す。直前の点に近すぎる場合は元の線をそのまま返す */
export function appendPoint(stroke: Stroke, point: Point): Stroke {
  const last = stroke.points[stroke.points.length - 1]
  if (last && distance(last, point) < MIN_POINT_DISTANCE) return stroke
  return { ...stroke, points: [...stroke.points, point] }
}

/** ペンで何か描いたか（消しゴムだけなら false） */
export function hasDrawing(strokes: readonly Stroke[]): boolean {
  return strokes.some((s) => s.tool !== 'eraser')
}

function distance(a: Point, b: Point): number {
  return Math.hypot(a.x - b.x, a.y - b.y)
}

function clamp(value: number, min: number, max: number): number {
  return Math.min(max, Math.max(min, value))
}

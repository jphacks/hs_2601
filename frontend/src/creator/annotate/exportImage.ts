/**
 * キャンバス描画と JPEG 書き出し。DOM / Canvas に依存する薄い関数だけを置く（単体テストしない）。
 * 写真と線は別レイヤー。消しゴムは線のレイヤーだけを消すので写真は消えない。
 */
import { JPEG_QUALITY, PEN_COLORS, type Point, type Size, type Stroke } from './strokes'

/** 読み込んだ写真。EXIF の回転は適用済み */
export interface LoadedImage {
  source: CanvasImageSource
  width: number
  height: number
  close: () => void
}

/** 写真を EXIF の向きどおりに読み込む。createImageBitmap が使えなければ <img> で読む */
export async function loadImage(blob: Blob): Promise<LoadedImage> {
  if (typeof createImageBitmap === 'function') {
    try {
      const bitmap = await createImageBitmap(blob, { imageOrientation: 'from-image' })
      return { source: bitmap, width: bitmap.width, height: bitmap.height, close: () => bitmap.close() }
    } catch {
      // 一部ブラウザはオプション付きで失敗するので <img> にフォールバックする
    }
  }
  return loadWithImgElement(blob)
}

async function loadWithImgElement(blob: Blob): Promise<LoadedImage> {
  const url = URL.createObjectURL(blob)
  try {
    const img = new Image()
    img.src = url
    await img.decode()
    return { source: img, width: img.naturalWidth, height: img.naturalHeight, close: () => {} }
  } catch {
    throw new Error('写真を読み込めませんでした（この形式には対応していない可能性があります）')
  } finally {
    URL.revokeObjectURL(url)
  }
}

function applyStrokeStyle(ctx: CanvasRenderingContext2D, stroke: Stroke): void {
  const color = stroke.tool === 'eraser' ? '#000' : PEN_COLORS[stroke.tool]
  ctx.globalCompositeOperation = stroke.tool === 'eraser' ? 'destination-out' : 'source-over'
  ctx.strokeStyle = color
  ctx.fillStyle = color
  ctx.lineWidth = stroke.width
  ctx.lineCap = 'round'
  ctx.lineJoin = 'round'
}

/** 線の一部（from → to）を描く。描画中の差分描画に使う */
export function drawSegment(
  ctx: CanvasRenderingContext2D,
  stroke: Stroke,
  from: Point,
  to: Point,
): void {
  applyStrokeStyle(ctx, stroke)
  ctx.beginPath()
  ctx.moveTo(from.x, from.y)
  ctx.lineTo(to.x, to.y)
  ctx.stroke()
}

/** 点（タップだけの線）を描く */
export function drawDot(ctx: CanvasRenderingContext2D, stroke: Stroke, at: Point): void {
  applyStrokeStyle(ctx, stroke)
  ctx.beginPath()
  ctx.arc(at.x, at.y, stroke.width / 2, 0, Math.PI * 2)
  ctx.fill()
}

/** 線 1 本を描く */
export function drawStroke(ctx: CanvasRenderingContext2D, stroke: Stroke): void {
  const [first, ...rest] = stroke.points
  if (!first) return
  if (rest.length === 0) {
    drawDot(ctx, stroke, first)
    return
  }
  applyStrokeStyle(ctx, stroke)
  ctx.beginPath()
  ctx.moveTo(first.x, first.y)
  rest.forEach((p) => ctx.lineTo(p.x, p.y))
  ctx.stroke()
}

/** 線のレイヤーを消してから全部の線を順に描き直す */
export function renderStrokes(ctx: CanvasRenderingContext2D, strokes: readonly Stroke[]): void {
  ctx.save()
  ctx.globalCompositeOperation = 'source-over'
  ctx.clearRect(0, 0, ctx.canvas.width, ctx.canvas.height)
  strokes.forEach((s) => drawStroke(ctx, s))
  ctx.restore()
}

/** 写真をキャンバスいっぱいに描く */
export function renderPhoto(ctx: CanvasRenderingContext2D, image: LoadedImage): void {
  ctx.drawImage(image.source, 0, 0, ctx.canvas.width, ctx.canvas.height)
}

function createCanvas(size: Size): { canvas: HTMLCanvasElement; ctx: CanvasRenderingContext2D } {
  const canvas = document.createElement('canvas')
  canvas.width = size.width
  canvas.height = size.height
  const ctx = canvas.getContext('2d')
  if (!ctx) throw new Error('この端末では画像を書き出せません')
  return { canvas, ctx }
}

function canvasToJpeg(canvas: HTMLCanvasElement, quality: number): Promise<Blob> {
  return new Promise((resolve, reject) => {
    canvas.toBlob(
      (blob) => (blob ? resolve(blob) : reject(new Error('画像の書き出しに失敗しました'))),
      'image/jpeg',
      quality,
    )
  })
}

/**
 * 写真の上に線のレイヤーを重ねて JPEG にする。
 * 線は別キャンバスで描いて（消しゴムはそこだけを消す）から写真に合成する。
 */
export async function exportAnnotatedJpeg(
  image: LoadedImage,
  size: Size,
  strokes: readonly Stroke[],
  quality: number = JPEG_QUALITY,
): Promise<Blob> {
  const base = createCanvas(size)
  base.ctx.fillStyle = '#fff' // 透過 PNG でも背景が黒くならないように
  base.ctx.fillRect(0, 0, size.width, size.height)
  renderPhoto(base.ctx, image)
  if (strokes.length > 0) {
    const overlay = createCanvas(size)
    renderStrokes(overlay.ctx, strokes)
    base.ctx.drawImage(overlay.canvas, 0, 0)
  }
  return canvasToJpeg(base.canvas, quality)
}

/**
 * 撮った写真を送信用の JPEG にする。
 * iPhone の HEIC や大きすぎる画像をそのまま送らないよう、EXIF の回転を反映して長辺を縮める。
 */
import { PHOTO_JPEG_QUALITY, PHOTO_MAX_EDGE_PX } from './constants'

export interface Size {
  width: number
  height: number
}

/** 長辺が maxEdge 以下になる大きさ。縦横比は保ち、拡大はしない */
export function fitWithin({ width, height }: Size, maxEdge: number): Size {
  if (width <= 0 || height <= 0) throw new Error(`画像の大きさが不正です: ${width}x${height}`)
  const scale = Math.min(1, maxEdge / Math.max(width, height))
  return {
    width: Math.max(1, Math.round(width * scale)),
    height: Math.max(1, Math.round(height * scale)),
  }
}

interface Decoded {
  source: CanvasImageSource
  size: Size
  release: () => void
}

/** createImageBitmap で読む。EXIF の向きを反映させる */
async function decodeWithBitmap(file: Blob): Promise<Decoded> {
  const bitmap = await createImageBitmap(file, { imageOrientation: 'from-image' })
  return {
    source: bitmap,
    size: { width: bitmap.width, height: bitmap.height },
    release: () => bitmap.close(),
  }
}

/** createImageBitmap が無い・失敗する端末向け。<img> は既定で EXIF の向きを反映する */
async function decodeWithImage(file: Blob): Promise<Decoded> {
  const url = URL.createObjectURL(file)
  const img = new Image()
  try {
    img.src = url
    await img.decode()
  } catch (e) {
    URL.revokeObjectURL(url)
    throw e
  }
  return {
    source: img,
    size: { width: img.naturalWidth, height: img.naturalHeight },
    release: () => URL.revokeObjectURL(url),
  }
}

async function decode(file: Blob): Promise<Decoded> {
  if (typeof createImageBitmap === 'function') {
    try {
      return await decodeWithBitmap(file)
    } catch {
      // Safari の一部などで失敗するので <img> で読み直す
    }
  }
  return decodeWithImage(file)
}

function canvasToJpeg(canvas: HTMLCanvasElement, quality: number): Promise<Blob> {
  return new Promise((resolve, reject) => {
    canvas.toBlob(
      (blob) => (blob ? resolve(blob) : reject(new Error('JPEG に変換できませんでした'))),
      'image/jpeg',
      quality,
    )
  })
}

/** 画像ファイルを JPEG（長辺 maxEdge 以下、EXIF の向きを反映）にする。開けない形式は例外 */
export async function toJpeg(
  file: Blob,
  maxEdge: number = PHOTO_MAX_EDGE_PX,
  quality: number = PHOTO_JPEG_QUALITY,
): Promise<Blob> {
  const decoded = await decode(file)
  try {
    const { width, height } = fitWithin(decoded.size, maxEdge)
    const canvas = document.createElement('canvas')
    canvas.width = width
    canvas.height = height
    const ctx = canvas.getContext('2d')
    if (!ctx) throw new Error('画像の変換に使う canvas を用意できませんでした')
    ctx.drawImage(decoded.source, 0, 0, width, height)
    return await canvasToJpeg(canvas, quality)
  } finally {
    decoded.release()
  }
}

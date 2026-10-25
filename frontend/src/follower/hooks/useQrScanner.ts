import jsQR from 'jsqr'
import { useEffect, useRef, useState } from 'react'

/** デコードを試みる間隔。毎フレームだと端末が熱くなるので間引く */
const SCAN_INTERVAL_MS = 150
/** デコードに使う画像の最大幅。これ以上は縮小してから渡す */
const MAX_SCAN_WIDTH = 640

const CAMERA_CONSTRAINTS: MediaStreamConstraints = {
  video: { facingMode: 'environment' },
  audio: false,
}

function cameraErrorMessage(e: unknown): string {
  if (e instanceof DOMException) {
    if (e.name === 'NotAllowedError') return 'カメラの使用が許可されませんでした'
    if (e.name === 'NotFoundError') return 'カメラが見つかりません'
    if (e.name === 'NotReadableError') return 'カメラを他のアプリが使用中です'
  }
  return 'カメラを起動できませんでした'
}

function decodeFrame(video: HTMLVideoElement, ctx: CanvasRenderingContext2D): string | null {
  const scale = Math.min(1, MAX_SCAN_WIDTH / video.videoWidth)
  const width = Math.floor(video.videoWidth * scale)
  const height = Math.floor(video.videoHeight * scale)
  if (width === 0 || height === 0) return null
  ctx.canvas.width = width
  ctx.canvas.height = height
  ctx.drawImage(video, 0, 0, width, height)
  const image = ctx.getImageData(0, 0, width, height)
  return jsQR(image.data, width, height, { inversionAttempts: 'dontInvert' })?.data ?? null
}

/**
 * カメラ映像を video に流し、QR を見つけたら onDetected を 1 回呼んで止まる。
 * active を false にすると停止してカメラを解放する。
 */
export function useQrScanner(active: boolean, onDetected: (text: string) => void) {
  const videoRef = useRef<HTMLVideoElement>(null)
  const onDetectedRef = useRef(onDetected)
  const [cameraError, setCameraError] = useState<string | null>(null)

  useEffect(() => {
    onDetectedRef.current = onDetected
  }, [onDetected])

  const supported = typeof navigator !== 'undefined' && !!navigator.mediaDevices?.getUserMedia

  useEffect(() => {
    const video = videoRef.current
    if (!active || !supported || !video) return

    let cancelled = false
    let stream: MediaStream | undefined
    let frame = 0
    let lastScanAt = 0
    const ctx = document.createElement('canvas').getContext('2d', { willReadFrequently: true })

    function stop() {
      cancelAnimationFrame(frame)
      stream?.getTracks().forEach((t) => t.stop())
      if (video) video.srcObject = null
    }

    function tick(now: number) {
      if (cancelled || !video) return
      if (ctx && video.readyState >= HTMLMediaElement.HAVE_CURRENT_DATA && now - lastScanAt >= SCAN_INTERVAL_MS) {
        lastScanAt = now
        const text = decodeFrame(video, ctx)
        if (text) {
          stop()
          onDetectedRef.current(text)
          return
        }
      }
      frame = requestAnimationFrame(tick)
    }

    navigator.mediaDevices
      .getUserMedia(CAMERA_CONSTRAINTS)
      .then(async (s) => {
        if (cancelled) {
          s.getTracks().forEach((t) => t.stop())
          return
        }
        stream = s
        video.srcObject = s
        await video.play()
        frame = requestAnimationFrame(tick)
      })
      .catch((e: unknown) => {
        if (!cancelled) setCameraError(cameraErrorMessage(e))
      })

    return () => {
      cancelled = true
      stop()
    }
  }, [active, supported])

  const error = supported ? cameraError : 'このブラウザではカメラを使えません'
  return { videoRef, error }
}

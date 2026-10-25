import type { RefObject } from 'react'

interface Props {
  videoRef: RefObject<HTMLVideoElement | null>
  /** カメラが起動できないときの理由。null なら映像が出ている */
  error: string | null
  onCancel: () => void
}

/** QR 読み取り画面。カメラ映像と枠、やめるボタンだけ */
export function QrScanner({ videoRef, error, onCancel }: Props) {
  return (
    <section>
      <h1 className="mt-6 mb-1.5 text-2xl">QR コードを読み取る</h1>
      <p className="m-0 text-sm text-muted">配布された QR コードを枠の中に映してください。</p>

      <div className="relative mt-5 aspect-square overflow-hidden rounded-[20px] bg-black">
        <video
          ref={videoRef}
          className="h-full w-full object-cover"
          playsInline
          muted
          autoPlay
        />
        <div className="pointer-events-none absolute inset-[12%] rounded-2xl border-4 border-white/80" />
        {error && (
          <p role="alert" className="absolute inset-x-4 bottom-4 rounded-xl bg-white/95 p-3 text-center text-sm text-red-700">
            {error}
          </p>
        )}
      </div>

      <button
        onClick={onCancel}
        className="mt-4 w-full rounded-[14px] border border-line-strong bg-white px-2.5 py-4 text-base font-bold text-brand"
      >
        やめる
      </button>
    </section>
  )
}

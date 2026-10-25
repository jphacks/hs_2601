import { useEffect, useMemo, useState, type JSX } from 'react'
import { buttonClass, secondaryClass } from '../components/styles'
import { AnnotatorToolbar } from './AnnotatorToolbar'
import { CaptionField } from './CaptionField'
import { normalizeCaption } from './caption'
import { DrawingSurface } from './DrawingSurface'
import { exportAnnotatedJpeg } from './exportImage'
import { fitExportSize } from './strokes'
import type { PhotoAnnotatorProps } from './types'
import { useAnnotation } from './useAnnotation'
import { useLoadedImage } from './useLoadedImage'

/** 開いている間は背後のページをスクロールさせない */
function useLockBodyScroll() {
  useEffect(() => {
    const previous = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    return () => {
      document.body.style.overflow = previous
    }
  }, [])
}

/**
 * 撮った写真に赤ペン・青ペンで書き込み、メッセージを添える全画面の編集画面。
 * 完了すると描画を焼き込んだ JPEG とメッセージを返す。
 */
export function PhotoAnnotator({
  source,
  initialCaption,
  onDone,
  onCancel,
}: PhotoAnnotatorProps): JSX.Element {
  useLockBodyScroll()
  const loaded = useLoadedImage(source)
  const annotation = useAnnotation(initialCaption)
  const [saving, setSaving] = useState(false)
  const [saveError, setSaveError] = useState<string | null>(null)
  const size = useMemo(() => (loaded.image ? fitExportSize(loaded.image) : null), [loaded.image])

  async function handleDone() {
    if (!loaded.image || !size || saving || annotation.captionTooLong) return
    setSaving(true)
    setSaveError(null)
    try {
      const blob = await exportAnnotatedJpeg(loaded.image, size, annotation.strokes)
      onDone({ blob, caption: normalizeCaption(annotation.caption), drawn: annotation.drawn })
    } catch (err) {
      console.error('写真の書き出しに失敗しました', err)
      setSaveError(err instanceof Error ? err.message : '画像の書き出しに失敗しました')
    } finally {
      setSaving(false)
    }
  }

  const canFinish = loaded.image !== null && !saving && !annotation.captionTooLong

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-label="写真に書き込む"
      className="fixed inset-0 z-50 flex flex-col bg-stone-900"
      style={{ paddingTop: 'env(safe-area-inset-top)' }}
    >
      <p className="px-4 py-2 text-center text-sm text-stone-200">
        指でなぞって目印を書き込めます
      </p>

      <div className="min-h-0 flex-1 px-2">
        {loaded.image && size ? (
          <DrawingSurface
            image={loaded.image}
            size={size}
            strokes={annotation.strokes}
            tool={annotation.tool}
            onStrokeEnd={annotation.addStroke}
          />
        ) : (
          <div className="flex h-full items-center justify-center px-4 text-center text-sm text-stone-300">
            {loaded.error ?? '写真を読み込み中...'}
          </div>
        )}
      </div>

      <div
        className="space-y-3 rounded-t-2xl bg-white p-3 text-stone-900"
        style={{ paddingBottom: 'calc(0.75rem + env(safe-area-inset-bottom))' }}
      >
        <AnnotatorToolbar
          tool={annotation.tool}
          canUndo={annotation.strokes.length > 0}
          onToolChange={annotation.setTool}
          onUndo={annotation.undo}
          onClear={annotation.clear}
        />
        <CaptionField
          value={annotation.caption}
          tooLong={annotation.captionTooLong}
          onChange={annotation.setCaption}
        />
        {saveError && <p className="text-sm text-red-600">{saveError}</p>}
        <div className="flex gap-3">
          <button type="button" className={secondaryClass} onClick={onCancel} disabled={saving}>
            キャンセル
          </button>
          <button
            type="button"
            className={`${buttonClass} disabled:opacity-50`}
            onClick={handleDone}
            disabled={!canFinish}
          >
            {saving ? '保存中...' : '完了'}
          </button>
        </div>
      </div>
    </div>
  )
}

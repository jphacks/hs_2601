import { PEN_COLORS, type Tool } from './strokes'

interface Props {
  tool: Tool
  canUndo: boolean
  onToolChange: (tool: Tool) => void
  onUndo: () => void
  onClear: () => void
}

const TOOLS: readonly { tool: Tool; label: string; swatch: string }[] = [
  { tool: 'red', label: '赤ペン', swatch: PEN_COLORS.red },
  { tool: 'blue', label: '青ペン', swatch: PEN_COLORS.blue },
  { tool: 'eraser', label: '消しゴム', swatch: '#ffffff' },
]

const baseButton =
  'flex flex-1 flex-col items-center gap-1 rounded-xl border px-1 py-2 text-xs font-medium disabled:opacity-40'

/** 赤ペン / 青ペン / 消しゴム と 1つ戻す / 全消去 */
export function AnnotatorToolbar({ tool, canUndo, onToolChange, onUndo, onClear }: Props) {
  return (
    <div className="flex gap-2" role="toolbar" aria-label="描画の道具">
      {TOOLS.map((t) => {
        const selected = t.tool === tool
        return (
          <button
            key={t.tool}
            type="button"
            aria-pressed={selected}
            onClick={() => onToolChange(t.tool)}
            className={`${baseButton} ${
              selected ? 'border-emerald-700 bg-emerald-50 ring-2 ring-emerald-700' : 'border-stone-300 bg-white'
            }`}
          >
            <span
              aria-hidden
              className="h-4 w-4 rounded-full border border-stone-400"
              style={{ backgroundColor: t.swatch }}
            />
            {t.label}
          </button>
        )
      })}
      <button
        type="button"
        onClick={onUndo}
        disabled={!canUndo}
        className={`${baseButton} border-stone-300 bg-white`}
      >
        <span aria-hidden className="h-4 leading-4">↶</span>
        戻す
      </button>
      <button
        type="button"
        onClick={onClear}
        disabled={!canUndo}
        className={`${baseButton} border-stone-300 bg-white text-red-600`}
      >
        <span aria-hidden className="h-4 leading-4">×</span>
        全消去
      </button>
    </div>
  )
}

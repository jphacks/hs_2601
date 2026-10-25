import { captionLength, MAX_CAPTION_LENGTH } from './caption'
import { inputClass } from '../components/styles'

interface Props {
  value: string
  tooLong: boolean
  onChange: (value: string) => void
}

/**
 * 写真に添えるメッセージ。日本語入力（変換中）を壊さないよう入力中は切り詰めず、
 * 上限を超えたら赤く表示して完了できなくする。
 */
export function CaptionField({ value, tooLong, onChange }: Props) {
  return (
    <label className="block">
      <span className="flex items-baseline justify-between text-sm">
        <span className="font-medium">メッセージ（任意）</span>
        <span className={tooLong ? 'font-semibold text-red-600' : 'text-stone-500'}>
          {captionLength(value)}/{MAX_CAPTION_LENGTH}
        </span>
      </span>
      <textarea
        rows={2}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder="例：赤い看板の角を右へ"
        className={`${inputClass} mt-1 resize-none py-2 text-base ${tooLong ? 'border-red-500' : ''}`}
      />
      {tooLong && (
        <span className="mt-1 block text-xs text-red-600">
          {MAX_CAPTION_LENGTH} 文字以内にしてください
        </span>
      )}
    </label>
  )
}

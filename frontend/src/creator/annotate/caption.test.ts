import { describe, expect, it } from 'vitest'
import { captionLength, isCaptionTooLong, MAX_CAPTION_LENGTH, normalizeCaption } from './caption'

describe('normalizeCaption', () => {
  it('前後の空白を除く', () => {
    expect(normalizeCaption('  赤い看板を右へ \n')).toBe('赤い看板を右へ')
  })

  it('空・空白だけ・null は null', () => {
    expect(normalizeCaption('')).toBeNull()
    expect(normalizeCaption('   \n　 ')).toBeNull()
    expect(normalizeCaption(null)).toBeNull()
    expect(normalizeCaption(undefined)).toBeNull()
  })

  it('改行は空白 1 つにまとめる', () => {
    expect(normalizeCaption('赤い看板\n\n  右へ')).toBe('赤い看板 右へ')
  })

  it('上限を超えた分は切り捨てる', () => {
    const long = 'あ'.repeat(MAX_CAPTION_LENGTH + 5)
    expect(normalizeCaption(long)).toBe('あ'.repeat(MAX_CAPTION_LENGTH))
    expect(normalizeCaption('abcdef', 3)).toBe('abc')
  })
})

describe('captionLength / isCaptionTooLong', () => {
  it('絵文字も 1 文字と数える', () => {
    expect(captionLength('🍙おにぎり')).toBe(5)
  })

  it('上限ちょうどは OK、超えたら NG', () => {
    expect(isCaptionTooLong('あ'.repeat(MAX_CAPTION_LENGTH))).toBe(false)
    expect(isCaptionTooLong('あ'.repeat(MAX_CAPTION_LENGTH + 1))).toBe(true)
  })
})

import { describe, expect, it } from 'vitest'
import { canEditAnswer } from '../../shared/utils/forms/answer-edit'

describe('editing submitted answers', () => {
  it('allows questions the team may correct', () => {
    for (const type of ['short_text', 'email', 'phone', 'radio', 'checkbox', 'date', 'rating', 'address', 'matrix'])
      expect(canEditAnswer({ type } as never)).toBe(true)
  })

  it('keeps evidence, derived and link values as sent', () => {
    for (const type of ['file_upload', 'image_upload', 'signature', 'payment', 'calculated', 'hidden'])
      expect(canEditAnswer({ type } as never)).toBe(false)
  })

  it('ignores layout blocks', () => {
    for (const type of ['section', 'paragraph', 'divider', 'image']) expect(canEditAnswer({ type } as never)).toBe(false)
  })
})

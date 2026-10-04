import { describe, expect, it } from 'vitest'
import { PAGE_PRESETS, pageDesignSchema, pageTokensOf, presetTokens, withPageDesign } from '../../shared/utils/forms/page-design'
import { defaultTheme } from '../../shared/utils/forms/theme'

describe('page designs', () => {
  const base = defaultTheme()

  it('every ready-made design is a valid page design with a unique key', () => {
    expect(new Set(PAGE_PRESETS.map(preset => preset.key)).size).toBe(PAGE_PRESETS.length)
    for (const preset of PAGE_PRESETS) expect(pageDesignSchema.safeParse(presetTokens(base, preset.patch)).success, preset.key).toBe(true)
  })

  it('applying a design changes only the page around the form', () => {
    const tokens = presetTokens(base, { frame: { style: 'side', tone: 'dark' }, page: { bg_type: 'color', bg: '#000000' } })
    const applied = withPageDesign(base, tokens)
    expect(applied.frame.style).toBe('side')
    expect(applied.page.bg).toBe('#000000')
    expect(applied.colors).toEqual(base.colors)
    expect(applied.container).toEqual(base.container)
  })

  it('reads the page tokens back as copies', () => {
    const tokens = pageTokensOf(base)
    tokens.frame.tone = 'brand'
    expect(base.frame.tone).toBe('light')
  })
})

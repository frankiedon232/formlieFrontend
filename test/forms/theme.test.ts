import { describe, expect, it } from 'vitest'
import {
  THEME_PRESETS,
  applyPatch,
  defaultTheme,
  pageBackground,
  readableOn,
  resolveTheme,
  themeSchema,
  themeVars,
} from '../../shared/utils/forms/theme'

describe('form themes', () => {
  it('uses the workspace brand colour and logo by default', () => {
    const theme = resolveTheme(undefined, { logo_url: '/api/v1/files/x', primary: '#0f766e' })
    expect(theme.colors.primary).toBe('#0f766e')
    expect(theme.header.show_logo).toBe(true)
    expect(resolveTheme(undefined).colors.primary).toBe('#18181b')
  })

  it('keeps valid stored tokens and drops invalid ones', () => {
    const theme = resolveTheme({ colors: { primary: '#123456' }, layout: 'nope', footer: { links: [{ label: 'x', href: 'javascript:alert(1)' }] } })
    expect(theme.colors.primary).toBe('#123456')
    expect(theme.layout).toBe('card')
    expect(theme.footer.links).toEqual([])
  })

  it('every starting point is a valid theme', () => {
    for (const preset of THEME_PRESETS) expect(themeSchema.safeParse(applyPatch(defaultTheme(), preset.patch)).success).toBe(true)
  })

  it('picks readable button text and builds the background', () => {
    expect(readableOn('#fafafa')).toBe('#18181b')
    expect(readableOn('#18181b')).toBe('#ffffff')
    const vars = themeVars(defaultTheme())
    expect(vars['--ui-primary']).toBe('#18181b')
    expect(pageBackground(applyPatch(defaultTheme(), { page: { bg_type: 'gradient' } }))).toContain('linear-gradient')
  })
})

describe('structural starting points', () => {
  it('every preset is a valid theme with distinct keys', () => {
    const keys = THEME_PRESETS.map(p => p.key)
    expect(new Set(keys).size).toBe(keys.length)
    for (const preset of THEME_PRESETS) {
      const theme = applyPatch(defaultTheme(), preset.patch)
      expect(resolveTheme(theme)).toEqual(theme)
    }
  })

  it('fills new tokens for themes saved before they existed', () => {
    const old = structuredClone(defaultTheme()) as unknown as Record<string, Record<string, unknown>>
    delete old.header!.band
    delete old.split!.panel
    delete old.footer!.style
    const theme = resolveTheme({ ...old, header: { ...old.header, subtitle: 'Hello' } })
    expect(theme.header.band).toBe('none')
    expect(theme.header.subtitle).toBe('Hello')
    expect(theme.split.panel).toBe('image')
    expect(theme.footer.style).toBe('plain')
  })
})

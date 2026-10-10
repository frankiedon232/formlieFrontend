import { describe, expect, it } from 'vitest'
import { THEME_FONTS, WEB_FONTS, fontStack, isWebFont } from '../../shared/utils/forms/fonts'
import {
  THEME_PRESETS,
  applyPatch,
  defaultTheme,
  pageBackground,
  readableOn,
  resolveTheme,
  visibleLinks,
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
    expect(theme.footer.links).toEqual([{ label: 'x', href: '' }])
    expect(visibleLinks(theme)).toEqual([])
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

describe('footer links', () => {
  it('keeps the footer while a link is half written and only shows complete links', () => {
    const theme = resolveTheme({
      footer: {
        enabled: true,
        links: [
          { label: 'New link', href: 'https://' },
          { label: '', href: 'https://example.org' },
          { label: 'Privacy', href: 'https://example.org/privacy' },
        ],
      },
    })
    expect(theme.footer.enabled).toBe(true)
    expect(theme.footer.links).toHaveLength(3)
    expect(visibleLinks(theme).map(l => l.label)).toEqual(['Privacy'])
  })
})

describe('theme block styles (sections, dividers, paragraphs, images)', () => {
  it('keep today’s look for themes saved before them', () => {
    const old = defaultTheme() as unknown as Record<string, unknown>
    delete old.blocks
    expect(resolveTheme(old).blocks).toEqual(defaultTheme().blocks)
    expect(defaultTheme().blocks).toMatchObject({ section: 'plain', divider: 'line', paragraph: 'plain', image_radius: 'md' })
  })

  it('come with every starting point, each valid', () => {
    const styles = new Set(THEME_PRESETS.filter(preset => preset.key !== 'workspace').map(preset => JSON.stringify(applyPatch(defaultTheme(), preset.patch).blocks)))
    expect(styles.size).toBeGreaterThan(5)
    for (const preset of THEME_PRESETS) expect(themeSchema.safeParse(applyPatch(defaultTheme(), preset.patch)).success).toBe(true)
  })
})

describe('theme fonts (leftovers L2)', () => {
  it('turn every font key into a stack with script fallbacks', () => {
    for (const key of THEME_FONTS) expect(fontStack(key)).toMatch(/sans-serif|serif|monospace/)
    expect(fontStack('playfair')).toMatch(/^'Playfair Display', 'Noto Serif'/)
    expect(fontStack('inter')).toContain("'Noto Sans Arabic'")
    expect(fontStack('nonsense')).toBe(fontStack('sans'))
    expect(Object.keys(WEB_FONTS).every(isWebFont)).toBe(true)
  })

  it('a theme accepts the new fonts and refuses unknown ones', () => {
    expect(themeSchema.safeParse({ ...defaultTheme(), typography: { ...defaultTheme().typography, font: 'lora' } }).success).toBe(true)
    expect(themeSchema.safeParse({ ...defaultTheme(), typography: { ...defaultTheme().typography, font: 'comic' } }).success).toBe(false)
  })
})

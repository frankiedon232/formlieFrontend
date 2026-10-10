/**
 * Fonts the form designer offers (F8; more fonts: leftovers L2, owner 2026-10-10). The web fonts are open-licence
 * Google fonts, self-hosted through @nuxt/fonts (nuxt.config `fonts.families`, no font package), so a form never
 * loads anything from another site; a browser only downloads the font a form actually uses. Every stack ends in
 * fonts for the other scripts (Arabic, Devanagari, Bengali, Chinese, Japanese, Korean), so text in any of the 20
 * languages has a font even where the chosen one has no letters for it.
 */

/** Script fallbacks after a sans font: Noto (Linux, Android), Segoe UI / Nirmala / YaHei / Yu Gothic / Malgun (Windows), PingFang / Hiragino (Apple). */
const SANS_TAIL = "'Noto Sans', 'Segoe UI', 'Noto Sans Arabic', 'Nirmala UI', 'PingFang SC', 'Microsoft YaHei', 'Hiragino Sans', 'Yu Gothic', 'Malgun Gothic', system-ui, sans-serif"
const SERIF_TAIL = "'Noto Serif', Georgia, 'Times New Roman', 'Noto Sans Arabic', 'Nirmala UI', 'PingFang SC', 'Microsoft YaHei', 'Hiragino Mincho ProN', 'Yu Mincho', serif"

/** Every font key a theme may hold: the five styles from the start, then the web fonts (leftovers L2). */
export const THEME_FONTS = [
  'sans', 'system', 'serif', 'rounded', 'mono',
  'inter', 'roboto', 'open_sans', 'montserrat', 'poppins', 'dm_sans', 'work_sans', 'ibm_plex_sans', 'noto_sans', 'nunito', 'cairo',
  'lora', 'merriweather', 'playfair', 'source_serif', 'noto_serif',
] as const
export type ThemeFont = (typeof THEME_FONTS)[number]
export type WebFont = Exclude<ThemeFont, 'sans' | 'system' | 'serif' | 'rounded' | 'mono'>

/** The web fonts: key → family name and kind. */
export const WEB_FONTS: Record<WebFont, { family: string; kind: 'sans' | 'serif' }> = {
  inter: { family: 'Inter', kind: 'sans' },
  roboto: { family: 'Roboto', kind: 'sans' },
  open_sans: { family: 'Open Sans', kind: 'sans' },
  montserrat: { family: 'Montserrat', kind: 'sans' },
  poppins: { family: 'Poppins', kind: 'sans' },
  dm_sans: { family: 'DM Sans', kind: 'sans' },
  work_sans: { family: 'Work Sans', kind: 'sans' },
  ibm_plex_sans: { family: 'IBM Plex Sans', kind: 'sans' },
  noto_sans: { family: 'Noto Sans', kind: 'sans' },
  nunito: { family: 'Nunito', kind: 'sans' },
  cairo: { family: 'Cairo', kind: 'sans' },
  lora: { family: 'Lora', kind: 'serif' },
  merriweather: { family: 'Merriweather', kind: 'serif' },
  playfair: { family: 'Playfair Display', kind: 'serif' },
  source_serif: { family: 'Source Serif 4', kind: 'serif' },
  noto_serif: { family: 'Noto Serif', kind: 'serif' },
}

const STYLES: Record<'sans' | 'system' | 'serif' | 'rounded' | 'mono', string> = {
  sans: `'Manrope', ${SANS_TAIL}`,
  system: `system-ui, -apple-system, 'Segoe UI', Roboto, ${SANS_TAIL}`,
  serif: `Georgia, Cambria, ${SERIF_TAIL}`,
  rounded: `ui-rounded, 'SF Pro Rounded', 'Nunito', ${SANS_TAIL}`,
  mono: "'JetBrains Mono', ui-monospace, SFMono-Regular, Menlo, Consolas, monospace",
}

/** The CSS font-family for a theme's font key (unknown keys fall back to the clean sans). */
export function fontStack(key: string): string {
  if (key in STYLES) return STYLES[key as keyof typeof STYLES]
  const font = WEB_FONTS[key as WebFont]
  if (!font) return STYLES.sans
  return `'${font.family}', ${font.kind === 'serif' ? SERIF_TAIL : SANS_TAIL}`
}

/** Is this one of the named web fonts (its name is shown as is, never translated)? */
export const isWebFont = (key: string): key is WebFont => key in WEB_FONTS

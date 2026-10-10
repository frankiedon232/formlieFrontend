/**
 * The mock assistant's designer (F19 M2): three designs from one brand colour, each a full set of theme
 * tokens over the workspace default. The colour is kept readable: buttons get a shade dark enough for
 * white text (WCAG contrast 4.5 : 1), backgrounds only a light tint of it. A mood word in the request
 * (calm, bold, formal, friendly, playful, minimal) picks the order. No outside service.
 */
import { applyPatch, defaultTheme, type FormTheme, type ThemePatch, type WorkspaceBranding } from '#shared/utils/forms/theme'

const rgb = (hex: string) => [1, 3, 5].map(at => parseInt(hex.slice(at, at + 2), 16)) as [number, number, number]
const hexOf = ([r, g, b]: number[]) => `#${[r, g, b].map(value => Math.round(Math.min(255, Math.max(0, value!))).toString(16).padStart(2, '0')).join('')}`
const mix = (a: string, b: string, share: number) => {
  const [x, y] = [rgb(a), rgb(b)]
  return hexOf(x.map((value, index) => value * share + y[index]! * (1 - share)))
}
const luminance = (hex: string) => {
  const [r, g, b] = rgb(hex).map(value => {
    const c = value / 255
    return c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4
  })
  return 0.2126 * r! + 0.7152 * g! + 0.0722 * b!
}
export const contrast = (a: string, b: string) => {
  const [l1, l2] = [luminance(a), luminance(b)].sort((x, y) => y - x)
  return (l1! + 0.05) / (l2! + 0.05)
}

/** The brand colour, darkened just enough for white text on it. */
export function readable(hex: string): string {
  let colour = hex.toLowerCase()
  for (let step = 0; step < 20 && contrast(colour, '#ffffff') < 4.5; step++) colour = mix(colour, '#000000', 0.9)
  return colour
}

export interface ThemeSuggestion {
  key: 'calm' | 'bold' | 'minimal'
  name: string
  description: string
  tokens: FormTheme
}

const MOODS: Record<ThemeSuggestion['key'], RegExp> = {
  calm: /\b(calm|soft|gentle|friendly|warm|care|health)\b/i,
  bold: /\b(bold|strong|vivid|playful|fun|bright|energetic|event)\b/i,
  minimal: /\b(minimal|clean|simple|formal|serious|corporate|legal|official)\b/i,
}

/** Three designs for a brand colour, the one that fits the mood first. */
export function themesFromColour(colour: string, mood = '', branding?: WorkspaceBranding): ThemeSuggestion[] {
  const brand = /^#[0-9a-f]{6}$/i.test(colour) ? colour.toLowerCase() : '#18181b'
  const primary = readable(brand)
  const base = defaultTheme({ logo_url: branding?.logo_url ?? null, primary })
  const ink = '#18181b'
  const patches: Record<ThemeSuggestion['key'], ThemePatch> = {
    calm: {
      page: { bg_type: 'color', bg: mix(brand, '#ffffff', 0.07) },
      container: { radius: 'xl', shadow: 'sm', border: false },
      colors: { primary, input_border: mix(brand, '#d4d4d8', 0.18) },
      inputs: { radius: 'md', style: 'outline' },
      buttons: { radius: 'md', variant: 'solid' },
      typography: { font: 'rounded' },
      blocks: { section: 'plain', section_color: 'primary', divider: 'space' },
    },
    bold: {
      page: { bg_type: 'gradient', bg: mix(brand, '#ffffff', 0.16), bg_to: mix(brand, '#ffffff', 0.04), gradient_angle: 160 },
      container: { radius: 'lg', shadow: 'md', border: false },
      colors: { primary, input_border: mix(brand, '#d4d4d8', 0.25) },
      header: { band: 'gradient', band_bg: primary, band_to: mix(primary, '#000000', 0.7) },
      buttons: { radius: 'full', variant: 'solid', full_width: true },
      inputs: { radius: 'md', style: 'soft' },
      blocks: { section: 'band', section_color: 'primary', divider: 'line' },
    },
    minimal: {
      layout: 'plain',
      page: { bg_type: 'color', bg: '#ffffff' },
      container: { radius: 'none', shadow: 'none', border: false },
      colors: { primary, text: ink },
      typography: { font: 'serif', heading_weight: 'bold' },
      inputs: { radius: 'none', style: 'underline' },
      buttons: { radius: 'none', variant: 'solid' },
      header: { band: 'accent', band_bg: primary },
      blocks: { section: 'underline', section_color: 'text', section_caps: true, divider: 'line' },
    },
  }
  const order = (Object.keys(MOODS) as ThemeSuggestion['key'][]).sort((a, b) => Number(MOODS[b].test(mood)) - Number(MOODS[a].test(mood)))
  return order.map(key => ({
    key,
    name: { calm: 'Calm', bold: 'Bold', minimal: 'Minimal' }[key],
    description: {
      calm: 'Soft tinted page, rounded fields and the brand colour on buttons and headings.',
      bold: 'A brand-coloured band at the top, a gradient page and full-width buttons.',
      minimal: 'A clean white page, serif headings and underlined fields with a brand accent.',
    }[key],
    tokens: applyPatch(base, patches[key]) as FormTheme,
  }))
}

/**
 * Form themes (F8, docs/API-CONTRACT.md → Theme tokens). A theme is a small set of design tokens
 * stored on the form (`schema.theme`, versioned with the form) and applied as CSS variables on the
 * rendered form page only — the portal never changes. A form without a theme uses the workspace
 * default (brand colour + logo from onboarding).
 */
import { z } from 'zod'

const hex = z.string().regex(/^#[0-9a-f]{6}$/i)
const httpsUrl = z.string().max(2000).regex(/^(https:\/\/\S+|\/api\/v1\/files\/[\w-]+)$/i)
const imageRef = httpsUrl.nullable()

export const THEME_FONTS = ['sans', 'system', 'serif', 'rounded', 'mono'] as const
export const THEME_LAYOUTS = ['card', 'plain', 'split', 'full'] as const
/**
 * The page around the form on its public link (F10, owner 2026-10-03): the organisation's
 * branding, a link to its website, quick facts and a secure-by-Formalie footer.
 *   branded   — top bar (logo, name, website) · form · footer
 *   spotlight — brand-colour hero with title, intro and facts; the form card overlaps it
 *   side      — branded side panel (sticky on wide screens) next to the form
 *   minimal   — the form with a slim footer
 * Embeds never show the page frame.
 */
export const THEME_FRAMES = ['branded', 'spotlight', 'side', 'minimal'] as const
export type ThemeFrame = (typeof THEME_FRAMES)[number]

export const themeSchema = z.object({
  layout: z.enum(THEME_LAYOUTS),
  page: z.object({
    bg_type: z.enum(['color', 'gradient', 'image']),
    bg: hex,
    bg_to: hex,
    gradient_angle: z.number().int().min(0).max(360),
    bg_image: imageRef,
    overlay: z.number().int().min(0).max(80),
  }),
  container: z.object({
    width: z.enum(['sm', 'md', 'lg', 'xl']),
    padding: z.enum(['sm', 'md', 'lg']),
    radius: z.enum(['none', 'sm', 'md', 'lg', 'xl']),
    border: z.boolean(),
    shadow: z.enum(['none', 'sm', 'md', 'lg']),
    bg: hex,
  }),
  typography: z.object({
    font: z.enum(THEME_FONTS),
    size: z.enum(['sm', 'md', 'lg']),
    heading_weight: z.enum(['medium', 'semibold', 'bold']),
  }),
  colors: z.object({
    primary: hex,
    text: hex,
    muted: hex,
    input_bg: hex,
    input_border: hex,
    error: hex,
  }),
  inputs: z.object({
    radius: z.enum(['none', 'sm', 'md', 'lg', 'full']),
    size: z.enum(['sm', 'md', 'lg']),
    style: z.enum(['outline', 'soft', 'underline']),
  }),
  buttons: z.object({
    radius: z.enum(['none', 'sm', 'md', 'lg', 'full']),
    variant: z.enum(['solid', 'outline', 'soft']),
    full_width: z.boolean(),
  }),
  header: z.object({
    show_logo: z.boolean(),
    logo: imageRef,
    cover: imageRef,
    cover_height: z.enum(['sm', 'md', 'lg']),
    show_title: z.boolean(),
    subtitle: z.string().max(300),
    align: z.enum(['start', 'center']),
    /** A coloured band behind logo / title / intro (no image needed). */
    /** none · color / gradient band across the top · accent = a quote-like block with a coloured edge (owner, 2026-10-03). */
    band: z.enum(['none', 'color', 'gradient', 'accent']),
    band_bg: hex,
    band_to: hex,
  }),
  split: z.object({
    image: imageRef,
    side: z.enum(['start', 'end']),
    /** Side panel fill; colour / gradient panels carry the logo, title and intro. */
    panel: z.enum(['image', 'color', 'gradient']),
    bg: hex,
    bg_to: hex,
  }),
  footer: z.object({
    enabled: z.boolean(),
    text: z.string().max(500),
    /** Stored as typed (a half-written link must not reset the footer); only complete links render — see visibleLinks. */
    links: z
      .array(
        z.object({
          label: z.string().max(60).catch(''),
          // https only (or on its way to it while typing); anything else is emptied, never kept.
          href: z
            .string()
            .max(2000)
            .refine(v => 'https://'.startsWith(v.toLowerCase()) || /^https:\/\//i.test(v))
            .catch(''),
        }),
      )
      .max(6),
    show_logo: z.boolean(),
    align: z.enum(['start', 'center']),
    /** plain = small text under the form · band = coloured bar (attached to the card). */
    style: z.enum(['plain', 'band']),
    bg: hex,
  }),
  thank_you: z.object({ show_icon: z.boolean() }),
  frame: z.object({
    style: z.enum(THEME_FRAMES),
    /** "Visit website" — the organisation's site (Settings → Company), never the portal. */
    show_website: z.boolean(),
    /** About N minutes · N questions · encrypted. */
    show_facts: z.boolean(),
    /** Top bar / side panel colour: the page's surface, dark, or the brand colour. */
    tone: z.enum(['light', 'dark', 'brand']),
  }),
})
export type FormTheme = z.infer<typeof themeSchema>

export interface WorkspaceBranding {
  logo_url: string | null
  primary: string | null
}

/** The workspace default — what every form looks like until someone designs it. */
export function defaultTheme(branding: WorkspaceBranding = { logo_url: null, primary: null }): FormTheme {
  return {
    layout: 'card',
    page: { bg_type: 'color', bg: '#f4f4f5', bg_to: '#e4e4e7', gradient_angle: 135, bg_image: null, overlay: 0 },
    container: { width: 'md', padding: 'md', radius: 'lg', border: true, shadow: 'sm', bg: '#ffffff' },
    typography: { font: 'sans', size: 'md', heading_weight: 'semibold' },
    colors: {
      primary: branding.primary && /^#[0-9a-f]{6}$/i.test(branding.primary) ? branding.primary : '#18181b',
      text: '#18181b',
      muted: '#71717a',
      input_bg: '#ffffff',
      input_border: '#d4d4d8',
      error: '#dc2626',
    },
    inputs: { radius: 'sm', size: 'md', style: 'outline' },
    buttons: { radius: 'sm', variant: 'solid', full_width: false },
    header: { show_logo: !!branding.logo_url, logo: null, cover: null, cover_height: 'md', show_title: true, subtitle: '', align: 'start', band: 'none', band_bg: '#18181b', band_to: '#3f3f46' },
    split: { image: null, side: 'start', panel: 'image', bg: '#18181b', bg_to: '#3f3f46' },
    footer: { enabled: false, text: '', links: [], show_logo: false, align: 'center', style: 'plain', bg: '#18181b' },
    thank_you: { show_icon: true },
    frame: { style: 'branded', show_website: true, show_facts: true, tone: 'light' },
  }
}

type DeepPartial<T> = { [K in keyof T]?: T[K] extends object ? (T[K] extends unknown[] ? T[K] : DeepPartial<T[K]>) : T[K] }
export type ThemePatch = DeepPartial<FormTheme>

/** Starting points (neutral, international). Each is a patch over the workspace default. */
export const THEME_PRESETS: { key: string; patch: ThemePatch }[] = [
  { key: 'workspace', patch: {} },
  {
    key: 'minimal',
    patch: {
      layout: 'plain',
      page: { bg_type: 'color', bg: '#ffffff' },
      container: { border: false, shadow: 'none', bg: '#ffffff' },
      inputs: { style: 'underline', radius: 'none' },
      buttons: { radius: 'none' },
    },
  },
  {
    key: 'soft',
    patch: {
      page: { bg_type: 'gradient', bg: '#eef2ff', bg_to: '#fdf2f8', gradient_angle: 135 },
      container: { radius: 'xl', shadow: 'md', border: false },
      colors: { primary: '#4f46e5', input_bg: '#f8fafc', input_border: '#e2e8f0' },
      inputs: { radius: 'lg', style: 'soft' },
      buttons: { radius: 'full' },
      typography: { font: 'rounded' },
    },
  },
  {
    key: 'bold',
    patch: {
      page: { bg_type: 'color', bg: '#0f766e' },
      container: { radius: 'md', shadow: 'lg', border: false },
      colors: { primary: '#0f766e' },
      typography: { heading_weight: 'bold', size: 'lg' },
      buttons: { full_width: true, radius: 'md' },
      header: { align: 'center' },
    },
  },
  {
    key: 'dark',
    patch: {
      page: { bg_type: 'color', bg: '#09090b' },
      container: { bg: '#18181b', border: true, shadow: 'none' },
      colors: { primary: '#fafafa', text: '#fafafa', muted: '#a1a1aa', input_bg: '#27272a', input_border: '#3f3f46', error: '#f87171' },
    },
  },
  {
    key: 'elegant',
    patch: {
      page: { bg_type: 'color', bg: '#faf7f2' },
      container: { radius: 'none', border: true, shadow: 'none', bg: '#fffdf9', padding: 'lg' },
      typography: { font: 'serif', heading_weight: 'medium' },
      colors: { primary: '#7c2d12', text: '#292524', muted: '#78716c', input_border: '#d6d3d1' },
      inputs: { radius: 'none', style: 'underline' },
      buttons: { radius: 'none', variant: 'outline' },
      header: { align: 'center' },
    },
  },
  // Header designs
  {
    key: 'banner',
    patch: {
      page: { bg_type: 'color', bg: '#f5f3ff' },
      container: { radius: 'xl', shadow: 'md', border: false },
      colors: { primary: '#6d28d9', input_border: '#ddd6fe' },
      inputs: { radius: 'md' },
      buttons: { radius: 'md' },
      header: { band: 'gradient', band_bg: '#6d28d9', band_to: '#db2777', align: 'center' },
    },
  },
  {
    key: 'ribbon',
    patch: {
      page: { bg_type: 'color', bg: '#f1f5f9' },
      container: { radius: 'sm', shadow: 'sm', border: true },
      colors: { primary: '#1d4ed8', input_border: '#cbd5e1' },
      typography: { font: 'system', heading_weight: 'bold' },
      header: { band: 'color', band_bg: '#1e3a8a' },
    },
  },
  // Footer design
  {
    key: 'grounded',
    patch: {
      layout: 'plain',
      page: { bg_type: 'color', bg: '#fafaf9' },
      colors: { primary: '#15803d', input_border: '#d6d3d1' },
      inputs: { style: 'soft', radius: 'md' },
      buttons: { radius: 'full', full_width: true },
      footer: { enabled: true, style: 'band', bg: '#14532d', align: 'center', show_logo: true },
    },
  },
  // Accent header designs (owner, 2026-10-04: these were side panels that squeezed the form)
  {
    key: 'sidebar',
    patch: {
      layout: 'card',
      page: { bg_type: 'color', bg: '#e2e8f0' },
      container: { width: 'lg', radius: 'lg', shadow: 'lg', border: false },
      colors: { primary: '#0f172a' },
      header: { band: 'accent', band_bg: '#0f172a' },
    },
  },
  {
    key: 'aurora',
    patch: {
      layout: 'card',
      page: { bg_type: 'gradient', bg: '#ecfeff', bg_to: '#f0fdf4', gradient_angle: 160 },
      container: { width: 'lg', radius: 'xl', shadow: 'md', border: false },
      typography: { font: 'rounded' },
      colors: { primary: '#0e7490', input_bg: '#f8fafc', input_border: '#cbd5e1' },
      inputs: { style: 'soft', radius: 'lg' },
      buttons: { radius: 'full' },
      header: { band: 'accent', band_bg: '#0e7490' },
    },
  },
  // Header + footer together
  {
    key: 'corporate',
    patch: {
      page: { bg_type: 'color', bg: '#f4f4f5' },
      container: { width: 'lg', radius: 'md', shadow: 'sm', border: true },
      colors: { primary: '#b45309' },
      typography: { heading_weight: 'bold' },
      buttons: { radius: 'sm' },
      header: { band: 'color', band_bg: '#27272a' },
      footer: { enabled: true, style: 'band', bg: '#27272a', align: 'start' },
    },
  },
]

/** A complete https address with a host (example.org/…). */
export const isHttpsLink = (href: string) => /^https:\/\/[^\s/.]+(\.[^\s/.]+)+(\/\S*)?$/i.test(href.trim())
/** Footer links that are complete: a label and an https address. */
export const visibleLinks = (theme: FormTheme) => theme.footer.links.filter(link => link.label.trim() && isHttpsLink(link.href))

/** CSS background for a colour / gradient fill (header band, side panel). */
export const fillBackground = (type: string, from: string, to: string, angle = 135) =>
  type === 'gradient' ? `linear-gradient(${angle}deg, ${from}, ${to})` : from

const isObject = (v: unknown): v is Record<string, unknown> => !!v && typeof v === 'object' && !Array.isArray(v)
function merge<T>(base: T, patch: unknown): T {
  if (!isObject(patch)) return base
  const out: Record<string, unknown> = { ...(base as Record<string, unknown>) }
  for (const [k, v] of Object.entries(patch)) {
    if (!(k in out) || v === undefined) continue
    out[k] = isObject(out[k]) && isObject(v) ? merge(out[k], v) : v
  }
  return out as T
}

/**
 * The full theme for a form: workspace default ← stored tokens. Anything invalid in the stored
 * tokens falls back to the default value, so a broken import can never break the form page.
 */
export function resolveTheme(stored: unknown, branding?: WorkspaceBranding): FormTheme {
  const base = defaultTheme(branding)
  const merged = merge(base, stored)
  const parsed = themeSchema.safeParse(merged)
  if (parsed.success) return withoutSidePanel(parsed.data)
  // Keep only the valid groups.
  const out = { ...base } as Record<string, unknown>
  for (const key of Object.keys(base) as (keyof FormTheme)[]) {
    const group = themeSchema.shape[key].safeParse((merged as Record<string, unknown>)[key])
    if (group.success) out[key] = group.data
  }
  return withoutSidePanel(out as FormTheme)
}
export const applyPatch = (theme: FormTheme, patch: ThemePatch) => merge(theme, patch)

/**
 * No side panel beside the form any more (owner, 2026-10-04: it squeezed the form). Forms and
 * saved themes that still say "split" become a card; a coloured panel becomes the quote-like accent
 * header in its colour (unless the header already has a band).
 */
function withoutSidePanel(theme: FormTheme): FormTheme {
  if (theme.layout !== 'split') return theme
  const header = theme.header.band === 'none' && theme.split.panel !== 'image' ? { ...theme.header, band: 'accent' as const, band_bg: theme.split.bg } : theme.header
  return { ...theme, layout: 'card', container: { ...theme.container, width: theme.container.width === 'xl' ? 'lg' : theme.container.width }, header }
}

// ── Colour helpers ────────────────────────────────────────────────────────────────────
function luminance(color: string) {
  const [r, g, b] = [1, 3, 5].map(i => parseInt(color.slice(i, i + 2), 16) / 255).map(c =>
    c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4,
  )
  return 0.2126 * r! + 0.7152 * g! + 0.0722 * b!
}
export function contrastRatio(a: string, b: string) {
  const [x, y] = [luminance(a), luminance(b)].sort((m, n) => n - m)
  return (x! + 0.05) / (y! + 0.05)
}
/** Black or white — whichever reads better on `color` (button text on the primary colour). */
export const readableOn = (color: string) => (contrastRatio(color, '#ffffff') >= contrastRatio(color, '#18181b') ? '#ffffff' : '#18181b')

// ── CSS variables (applied on the form page root) ─────────────────────────────────────
const RADIUS: Record<string, string> = { none: '0px', sm: '0.25rem', md: '0.375rem', lg: '0.5rem', xl: '0.75rem', full: '9999px' }
/** Nuxt UI rounds controls at 1.5 × --ui-radius, so the variable is the target ÷ 1.5. */
const UI_RADIUS: Record<string, string> = { none: '0px', sm: '0.1667rem', md: '0.25rem', lg: '0.3333rem', xl: '0.5rem', full: '9999px' }
const FONT: Record<string, string> = {
  sans: "'Manrope', ui-sans-serif, system-ui, sans-serif",
  system: "system-ui, -apple-system, 'Segoe UI', Roboto, 'Noto Sans', sans-serif",
  serif: "Georgia, Cambria, 'Times New Roman', 'Noto Serif', serif",
  rounded: "ui-rounded, 'SF Pro Rounded', 'Nunito', 'Segoe UI', system-ui, sans-serif",
  mono: "'JetBrains Mono', ui-monospace, SFMono-Regular, Menlo, monospace",
}
const SIZE: Record<string, string> = { sm: '15px', md: '16px', lg: '17px' }

/**
 * Nuxt UI reads its colours from `--ui-*` variables, so setting them on the form root re-themes
 * every input, button and text inside — without touching the portal around it.
 */
export function themeVars(theme: FormTheme): Record<string, string> {
  const c = theme.colors
  const mix = (a: string, b: string, p: number) => `color-mix(in oklab, ${a} ${p}%, ${b})`
  return {
    '--ui-primary': c.primary,
    '--ui-text-inverted': readableOn(c.primary),
    '--ui-text': c.text,
    '--ui-text-highlighted': c.text,
    '--ui-text-toned': mix(c.text, c.muted, 50),
    '--ui-text-muted': c.muted,
    '--ui-text-dimmed': mix(c.muted, theme.container.bg, 70),
    '--ui-bg': c.input_bg,
    '--ui-bg-muted': mix(c.input_bg, c.text, 96),
    '--ui-bg-elevated': mix(c.input_bg, c.text, 93),
    '--ui-bg-accented': mix(c.input_bg, c.text, 86),
    '--ui-bg-inverted': c.text,
    '--ui-border': mix(c.input_border, theme.container.bg, 60),
    '--ui-border-muted': mix(c.input_border, theme.container.bg, 50),
    '--ui-border-accented': c.input_border,
    '--ui-border-inverted': c.text,
    '--ui-error': c.error,
    '--ui-radius': UI_RADIUS[theme.inputs.radius]!,
    '--form-container-bg': theme.container.bg,
    '--form-button-radius': RADIUS[theme.buttons.radius]!,
    '--form-input-radius': RADIUS[theme.inputs.radius]!,
    '--form-font': FONT[theme.typography.font]!,
    '--form-font-size': SIZE[theme.typography.size]!,
  }
}

/** The page background as one CSS `background` value. */
export function pageBackground(theme: FormTheme): string {
  const p = theme.page
  if (p.bg_type === 'gradient') return `linear-gradient(${p.gradient_angle}deg, ${p.bg}, ${p.bg_to})`
  if (p.bg_type === 'image' && p.bg_image) {
    const shade = `rgba(0, 0, 0, ${p.overlay / 100})`
    return `linear-gradient(${shade}, ${shade}), url("${p.bg_image.replace(/"/g, '')}") center / cover no-repeat, ${p.bg}`
  }
  return p.bg
}

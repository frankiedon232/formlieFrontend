/**
 * The portal's look per workspace (F14 M6, owner 2026-10-05): colours, shape, type, sidebar, header,
 * footer and page layout. Everyone in the workspace sees it; public forms keep their own themes.
 * Light and dark (leftovers L3, owner 2026-10-10): a default mode for people who haven't picked one, and
 * optionally other colours in dark mode.
 */

export const APPEARANCE_PRIMARIES = ['mono', 'brand', 'indigo', 'blue', 'sky', 'teal', 'emerald', 'green', 'amber', 'orange', 'red', 'rose', 'pink', 'violet', 'purple'] as const
export const APPEARANCE_NEUTRALS = ['zinc', 'slate', 'gray', 'neutral', 'stone'] as const
export const APPEARANCE_RADII = ['none', 'sm', 'md', 'lg', 'xl'] as const
export const APPEARANCE_FONTS = ['manrope', 'system', 'serif', 'rounded'] as const

export interface AppearanceSettings {
  /** The preset it started from ('custom' once changed). */
  preset: string
  /** mono = black / white actions (Formalie), brand = the brand colour from Branding, else a palette. */
  primary: (typeof APPEARANCE_PRIMARIES)[number]
  neutral: (typeof APPEARANCE_NEUTRALS)[number]
  background: 'plain' | 'tinted'
  radius: (typeof APPEARANCE_RADII)[number]
  font: (typeof APPEARANCE_FONTS)[number]
  text_size: 'sm' | 'md' | 'lg'
  rail: 'light' | 'dark'
  menu: 'light' | 'dark'
  menu_badges: boolean
  header: { breadcrumbs: boolean; search: boolean }
  footer: boolean
  content_width: 'full' | 'centred'
  density: 'comfortable' | 'compact'
  /** The mode for people who haven't picked one themselves (their own choice always wins). */
  default_mode: 'system' | 'light' | 'dark'
  /** Other colours in dark mode; null = the same colours in both modes. */
  dark: AppearanceDark | null
}

/** The colours used in dark mode when they differ from light mode. */
export interface AppearanceDark {
  primary: (typeof APPEARANCE_PRIMARIES)[number]
  neutral: (typeof APPEARANCE_NEUTRALS)[number]
  background: 'plain' | 'tinted'
}

export const FORMALIE_APPEARANCE: AppearanceSettings = {
  preset: 'formalie',
  primary: 'mono',
  neutral: 'zinc',
  background: 'plain',
  radius: 'md',
  font: 'manrope',
  text_size: 'md',
  rail: 'light',
  menu: 'light',
  menu_badges: true,
  header: { breadcrumbs: true, search: true },
  footer: true,
  content_width: 'full',
  density: 'comfortable',
  default_mode: 'system',
  dark: null,
}

/** Ready-made looks: a start, everything stays adjustable. */
export const APPEARANCE_PRESETS: Record<string, Partial<AppearanceSettings>> = {
  formalie: {},
  midnight: { neutral: 'slate', rail: 'dark', menu: 'dark' },
  ocean: { primary: 'blue', neutral: 'slate', radius: 'lg', background: 'tinted' },
  forest: { primary: 'emerald', neutral: 'stone', background: 'tinted' },
  sunset: { primary: 'orange', neutral: 'stone', radius: 'xl', font: 'rounded' },
  classic: { primary: 'indigo', neutral: 'gray', radius: 'sm', font: 'system' },
  brand: { primary: 'brand', rail: 'dark' },
}

/**
 * The workspace's main colour as a plain hex value, for files made outside the browser (the PDF
 * report): black and white → the portal's ink, brand → the Branding colour, else the palette
 * colour's 600 shade (the shade the portal uses in light mode). Owner 2026-10-05: exports follow the
 * application's look, not the form's theme.
 */
import type { AppearanceSettings } from '#shared/types/appearance'

export const APP_INK = '#18181b'

const SHADE_600: Record<string, string> = {
  indigo: '#4f46e5',
  blue: '#2563eb',
  sky: '#0284c7',
  teal: '#0d9488',
  emerald: '#059669',
  green: '#16a34a',
  amber: '#d97706',
  orange: '#ea580c',
  red: '#dc2626',
  rose: '#e11d48',
  pink: '#db2777',
  violet: '#7c3aed',
  purple: '#9333ea',
}

export function appearanceInk(appearance: Pick<AppearanceSettings, 'primary'> | null | undefined, brandColor?: string | null): string {
  if (!appearance || appearance.primary === 'mono') return APP_INK
  if (appearance.primary === 'brand') return brandColor && /^#[0-9a-f]{6}$/i.test(brandColor) ? brandColor : APP_INK
  return SHADE_600[appearance.primary] ?? APP_INK
}

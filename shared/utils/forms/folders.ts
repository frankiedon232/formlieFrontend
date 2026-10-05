/**
 * Folder colours (F11 M4, owner 2026-10-02: coloured folder icons in the sidebar). A small identity
 * palette, the same tones as the sidebar's resource icons; `ink` is the default. Each key maps to
 * Tailwind classes for the icon (text) and swatches (bg), so the palette lives in one place.
 */
export const FOLDER_COLORS = {
  ink: { text: 'text-(--ui-text-highlighted)', bg: 'bg-inverted' },
  red: { text: 'text-red-500', bg: 'bg-red-500' },
  orange: { text: 'text-orange-500', bg: 'bg-orange-500' },
  amber: { text: 'text-amber-500', bg: 'bg-amber-500' },
  green: { text: 'text-green-600', bg: 'bg-green-600' },
  teal: { text: 'text-teal-500', bg: 'bg-teal-500' },
  violet: { text: 'text-violet-600', bg: 'bg-violet-600' },
  pink: { text: 'text-pink-500', bg: 'bg-pink-500' },
} as const
export type FolderColor = keyof typeof FOLDER_COLORS
export const FOLDER_COLOR_KEYS = Object.keys(FOLDER_COLORS) as FolderColor[]
export const folderColor = (color: string | null | undefined) => FOLDER_COLORS[(color ?? 'ink') as FolderColor] ?? FOLDER_COLORS.ink

/**
 * Folder colours (F11 M4, owner 2026-10-02: coloured folder icons in the sidebar; 2026-10-05: more
 * colours and a picker for any other). Eighteen named colours, plus any custom colour saved as
 * `#rrggbb`. `ink` is the default. Named colours map to Tailwind classes (icon text, swatch bg);
 * a custom colour comes back as an inline style, so every place shows both `class` and `style`.
 */
export const FOLDER_COLORS = {
  ink: { text: 'text-(--ui-text-highlighted)', bg: 'bg-inverted' },
  red: { text: 'text-red-500', bg: 'bg-red-500' },
  orange: { text: 'text-orange-500', bg: 'bg-orange-500' },
  amber: { text: 'text-amber-500', bg: 'bg-amber-500' },
  yellow: { text: 'text-yellow-500', bg: 'bg-yellow-500' },
  lime: { text: 'text-lime-500', bg: 'bg-lime-500' },
  green: { text: 'text-green-600', bg: 'bg-green-600' },
  emerald: { text: 'text-emerald-500', bg: 'bg-emerald-500' },
  teal: { text: 'text-teal-500', bg: 'bg-teal-500' },
  cyan: { text: 'text-cyan-500', bg: 'bg-cyan-500' },
  sky: { text: 'text-sky-500', bg: 'bg-sky-500' },
  blue: { text: 'text-blue-600', bg: 'bg-blue-600' },
  indigo: { text: 'text-indigo-500', bg: 'bg-indigo-500' },
  violet: { text: 'text-violet-600', bg: 'bg-violet-600' },
  purple: { text: 'text-purple-500', bg: 'bg-purple-500' },
  fuchsia: { text: 'text-fuchsia-500', bg: 'bg-fuchsia-500' },
  pink: { text: 'text-pink-500', bg: 'bg-pink-500' },
  rose: { text: 'text-rose-500', bg: 'bg-rose-500' },
} as const
export type FolderColor = keyof typeof FOLDER_COLORS
export const FOLDER_COLOR_KEYS = Object.keys(FOLDER_COLORS) as FolderColor[]
export const isCustomColor = (color: string | null | undefined): color is string => typeof color === 'string' && /^#[0-9a-f]{6}$/i.test(color)

/** Classes and styles for a folder's colour: `text` / `textStyle` for the icon, `bg` / `bgStyle` for a swatch. */
export function folderColor(color: string | null | undefined): { text: string; bg: string; textStyle?: { color: string }; bgStyle?: { backgroundColor: string } } {
  if (isCustomColor(color)) return { text: '', bg: '', textStyle: { color }, bgStyle: { backgroundColor: color } }
  return FOLDER_COLORS[(color ?? 'ink') as FolderColor] ?? FOLDER_COLORS.ink
}

/**
 * The folders the sidebar shows (owner 2026-10-05): pinned first (in pin order), then the most
 * recently opened, then the busiest; each once, at most `max`.
 */
export function pickSidebarFolders<T extends { id: string; count: number }>(folders: T[], pinned: string[], recent: string[], max = 5): T[] {
  const byId = new Map(folders.map(folder => [folder.id, folder]))
  const ordered = [...pinned.map(id => byId.get(id)), ...recent.map(id => byId.get(id)), ...[...folders].sort((a, b) => b.count - a.count)].filter((folder): folder is T => !!folder)
  return [...new Map(ordered.map(folder => [folder.id, folder])).values()].slice(0, max)
}

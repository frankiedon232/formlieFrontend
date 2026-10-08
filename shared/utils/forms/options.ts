/**
 * Option values (F15): the stored value of an option, made from its label when people don't set one,
 * the same plain style as field keys (lower case, accents dropped, a–z / 0–9 and "_"; "option" when the
 * label has no Latin letters), unique within the list ("_2", "_3"…). Labels change freely later; the
 * value stays, so old answers keep reading.
 */

/** The most levels a list may have (owner 2026-10-07: four, more becomes a mess). */
export const MAX_LIST_LEVELS = 4

/**
 * Long lists (F15 M3, search as you type): a dropdown or multi-select with more than SEARCH_FROM options
 * shows a search box (the field's `props.search` turns it on or off by hand); the public form page gets
 * fields with more than REMOTE_FROM options without them and asks the server as people type (only fields
 * without a level above: lower levels are already narrowed by the choice above). The builder shows a
 * summary instead of every row from LONG_FROM options of a list.
 */
export const SEARCH_FROM = 50
export const REMOTE_FROM = 300
export const LONG_FROM = 100
/** Lists may hold this many options, and so may a field filled from one. */
export const MAX_OPTIONS = 20000

type SearchField = { type: string; options?: { value: string }[] | null; props?: Record<string, unknown> | null; option_parent?: string | null; options_remote?: { total: number } | null }
/** A dropdown / multi-select that searches as you type. */
export function searchesAsYouType(field: SearchField): boolean {
  if (field.type !== 'dropdown' && field.type !== 'multi_select') return false
  if (field.options_remote) return true
  const set = field.props?.search
  return typeof set === 'boolean' ? set : (field.options?.length ?? 0) > SEARCH_FROM
}
/** Options served by the server on the public page (not sent with the form). */
export const servedRemotely = (field: SearchField) => !field.option_parent && (field.type === 'dropdown' || field.type === 'multi_select') && (field.options?.length ?? 0) > REMOTE_FROM

export function valueFromLabel(label: string): string {
  const base = label
    .normalize('NFKD')
    .replace(/[̀-ͯ]/g, '')
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '_')
    .replace(/^_+|_+$/g, '')
    .slice(0, 60)
  return base || 'option'
}

/** A value not yet taken in `taken` (compared without case). */
export function uniqueValue(wanted: string, taken: Iterable<string>): string {
  const used = new Set([...taken].map(value => value.toLowerCase()))
  if (!used.has(wanted.toLowerCase())) return wanted
  for (let n = 2; ; n++) if (!used.has(`${wanted}_${n}`.toLowerCase())) return `${wanted}_${n}`
}

/** Values that appear more than once (without case), for a "values must differ" message. */
export const repeatedValues = (values: string[]) => {
  const seen = new Set<string>()
  const repeated = new Set<string>()
  for (const value of values) (seen.has(value.toLowerCase()) ? repeated : seen).add(value.toLowerCase())
  return repeated
}

type ListLike = { levels?: { key: string; label: string }[]; options: { value: string; label: string; score?: number; active?: boolean; level?: number; parent?: string }[] }

/** The named levels of a list with levels (two or more), else null for a plain list. */
export const levelsOf = (list: Pick<ListLike, 'levels'>) => (list.levels && list.levels.length > 1 ? list.levels : null)

/** Options offered at a level: active ones whose whole path above is active too. */
function offeredAt(list: ListLike, level: number) {
  let open = new Set<string | undefined>([undefined])
  let result: ListLike['options'] = []
  for (let at = 0; at <= level; at++) {
    result = list.options.filter(option => (option.level ?? 0) === at && option.active !== false && (at === 0 || open.has(option.parent)))
    open = new Set(result.map(option => option.value))
  }
  return result
}

/** What a level field gets from a list (level 0 for plain lists): value / label / score, and the option it sits under. */
export const offeredOptions = (list: ListLike, level = 0) =>
  offeredAt(list, level).map(({ value, label, score, parent }) => ({ value, label, ...(score !== undefined ? { score } : {}), ...(level > 0 && parent !== undefined ? { parent } : {}) }))

/** A field's options still match its list at its level (same values, labels, scores and parents, same order). */
export const matchesList = (options: { value: string; label: string; score?: number; parent?: string }[] | null | undefined, list: ListLike, level = 0) => {
  const wanted = offeredOptions(list, level)
  return !!options && options.length === wanted.length && options.every((option, i) => option.value === wanted[i]!.value && option.label === wanted[i]!.label && (option.score ?? null) === (wanted[i]!.score ?? null) && (option.parent ?? null) === ((wanted[i] as { parent?: string }).parent ?? null))
}

const fold = (text: string) => text.normalize('NFKD').replace(/[̀-ͯ]/g, '').toLowerCase()
/**
 * Search as you type on the server (F15 M3): options whose label contains `q`, without minding case or
 * accents ("sao" finds "São Paulo"); those that start with it first; at most `limit`, with how many match.
 */
export function matchOptions<T extends { label: string }>(options: T[], q: string, limit = 50): { items: T[]; total: number } {
  const wanted = fold(q.trim()).slice(0, 100)
  if (!wanted) return { items: options.slice(0, limit), total: options.length }
  const matches = options.filter(option => fold(option.label).includes(wanted))
  const first = matches.filter(option => fold(option.label).startsWith(wanted))
  const rest = matches.filter(option => !fold(option.label).startsWith(wanted))
  return { items: [...first, ...rest].slice(0, limit), total: matches.length }
}

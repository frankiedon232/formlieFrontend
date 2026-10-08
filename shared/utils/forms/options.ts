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
/**
 * Lists above LIVE_FROM options live only in the database (owner 2026-10-08: "every form should come from
 * the DB when its list is bigger than 20, if not the server will have a bottleneck"): forms keep no copy,
 * follow the list as soon as it is saved, and load its options from the server as people type. Lists of
 * 20 or fewer are copied into forms (Update forms). Choice fields typed by hand load from the server above
 * the same count on the public page.
 */
export const LIVE_FROM = 20
export const REMOTE_FROM = LIVE_FROM
export const LONG_FROM = 100
/** Lists may hold this many options, and so may a field filled from one. */
export const MAX_OPTIONS = 20000
/**
 * Large dynamic lists (F15 M5, owner 2026-10-08: "do 1 and 2"): a list switched to Large holds up to
 * this many. Its options stay on the server: forms keep them there (the browser gets `options_large`
 * instead, with how many and which choices above have options under them) and load each level for the
 * choice above as people type. Only dropdowns and multi-selects can show a large list.
 */
export const MAX_LARGE_OPTIONS = 200000
export const maxOptionsOf = (list: { large?: boolean }) => (list.large ? MAX_LARGE_OPTIONS : MAX_OPTIONS)
/** A list that lives only in the database (large, or above LIVE_FROM active options; the builder's copy of such a list carries `level_counts`). */
export const keptOnServer = (list: { large?: boolean; level_counts?: number[]; options: { active?: boolean }[] }) =>
  !!list.large || !!list.level_counts || list.options.filter(option => option.active !== false).length > LIVE_FROM
/** Field types a list kept on the server can be shown as. */
export const LARGE_LIST_TYPES = ['dropdown', 'multi_select'] as const

type SearchField = { type: string; options?: { value: string }[] | null; props?: Record<string, unknown> | null; option_parent?: string | null; options_remote?: { total: number } | null; options_large?: { total: number } | null }
/** A dropdown / multi-select that searches as you type. */
export function searchesAsYouType(field: SearchField): boolean {
  if (field.options_remote || field.options_large) return true
  if (field.type !== 'dropdown' && field.type !== 'multi_select') return false
  const set = field.props?.search
  return typeof set === 'boolean' ? set : (field.options?.length ?? 0) > SEARCH_FROM
}
/** Options served by the server on the public page (not sent with the form). */
export const servedRemotely = (field: SearchField) =>
  ['dropdown', 'multi_select', 'radio', 'checkbox'].includes(field.type) && (!!field.options_large || (!field.option_parent && (field.options?.length ?? 0) > REMOTE_FROM))

export function valueFromLabel(label: string): string {
  const base = label
    .normalize('NFKD')
    .replace(/[\u0300-\u036f]/g, '')
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

type Attrs = Record<string, string | number>
type ListLike = { levels?: { key: string; label: string }[]; columns?: { key: string; label: string }[]; options: { value: string; label: string; score?: number; active?: boolean; level?: number; parent?: string; attrs?: Attrs }[] }

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

/** Only details for the list's own columns, without empty ones. */
const detailsOf = (attrs: Attrs | undefined, columns: ListLike['columns']) => {
  if (!attrs || !columns?.length) return undefined
  const kept = Object.fromEntries(columns.filter(column => attrs[column.key] !== undefined && attrs[column.key] !== '').map(column => [column.key, attrs[column.key]!]))
  return Object.keys(kept).length ? kept : undefined
}

/** What a level field gets from a list (level 0 for plain lists): value / label / score, the option it sits under, and its details (F15 M4). */
export const offeredOptions = (list: ListLike, level = 0) =>
  offeredAt(list, level).map(({ value, label, score, parent, attrs }) => {
    const details = detailsOf(attrs, list.columns)
    return { value, label, ...(score !== undefined ? { score } : {}), ...(level > 0 && parent !== undefined ? { parent } : {}), ...(details ? { attrs: details } : {}) }
  })

/** A field's options still match its list at its level (same values, labels, scores and parents, same order). */
export const matchesList = (options: { value: string; label: string; score?: number; parent?: string; attrs?: Attrs }[] | null | undefined, list: ListLike, level = 0) => {
  const wanted = offeredOptions(list, level)
  return !!options && options.length === wanted.length && options.every((option, i) => option.value === wanted[i]!.value && option.label === wanted[i]!.label && (option.score ?? null) === (wanted[i]!.score ?? null) && (option.parent ?? null) === ((wanted[i] as { parent?: string }).parent ?? null) && JSON.stringify(option.attrs ?? null) === JSON.stringify((wanted[i] as { attrs?: Attrs }).attrs ?? null))
}

/** Active options per level of a list (the builder's summary of a large list, F15 M5). */
export const levelCounts = (list: ListLike) => Array.from({ length: levelsOf(list)?.length ?? 1 }, (_, level) => offeredAt(list, level).length)

const fold = (text: string) => text.normalize('NFKD').replace(/[\u0300-\u036f]/g, '').toLowerCase()
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

/**
 * A server-side lookup on one field's options (public page and builder, F15 M3 / M5): `values` gives the
 * labels of chosen options, `parents` keeps a lower level to what is under the choices above, `q` searches.
 */
export function lookupOptions(options: { value: string; label: string; parent?: string; attrs?: Attrs }[], query: { q?: string; values?: string[] | null; parents?: string[] | null }) {
  const under = query.parents ? new Set(query.parents) : null
  // Details come along, so auto-fill works in the browser too (F15 M4)
  const pool = (under ? options.filter(option => option.parent !== undefined && under.has(option.parent)) : options).map(option => ({ value: option.value, label: option.label, ...(option.attrs ? { attrs: option.attrs } : {}) }))
  if (query.values) {
    const wanted = new Set(query.values)
    return { items: pool.filter(option => wanted.has(option.value)), total: query.values.length }
  }
  return matchOptions(pool, query.q ?? '')
}

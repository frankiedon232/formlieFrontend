/**
 * Option values (F15): the stored value of an option, made from its label when people don't set one,
 * the same plain style as field keys (lower case, accents dropped, a–z / 0–9 and "_"; "option" when the
 * label has no Latin letters), unique within the list ("_2", "_3"…). Labels change freely later; the
 * value stays, so old answers keep reading.
 */

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

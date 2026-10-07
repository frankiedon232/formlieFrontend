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

/** What a field gets from a list: its active options, value / label / score only (translations travel separately). */
export const offeredOptions = (list: { options: { value: string; label: string; score?: number; active?: boolean }[] }) =>
  list.options.filter(option => option.active !== false).map(({ value, label, score }) => ({ value, label, ...(score !== undefined ? { score } : {}) }))

/** A field's options still match its list (same values, labels and scores, same order). */
export const matchesList = (options: { value: string; label: string; score?: number }[] | null | undefined, list: Parameters<typeof offeredOptions>[0]) => {
  const wanted = offeredOptions(list)
  return !!options && options.length === wanted.length && options.every((option, i) => option.value === wanted[i]!.value && option.label === wanted[i]!.label && (option.score ?? null) === (wanted[i]!.score ?? null))
}

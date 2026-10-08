/**
 * Choice answers in the public API (owner 2026-10-08: a record showed `running_shoes_air_footwear`
 * instead of "Footwear"). Answers are stored as option values (codes that never change); the API
 * speaks labels:
 * - out (GET, records, examples): each chosen value becomes its option's label;
 * - in (POST, PUT, GET filters): a label or a value is accepted; labels become values before the
 *   form's own checks. A label used by two options of one level (a city name under two regions)
 *   is settled by the choice one level up.
 */
interface OptionLike {
  value: string
  label: string
  parent?: string
}
interface FieldLike {
  key: string
  options?: OptionLike[] | null
  option_parent?: string | null
  id?: string
}

const labelOf = (options: OptionLike[], value: unknown) => (typeof value === 'string' ? (options.find(option => option.value === value)?.label ?? value) : value)

/** A stored answer as the API returns it: option labels instead of values. */
export function choiceOut(field: FieldLike, value: unknown): unknown {
  const options = field.options ?? []
  if (!options.length || value == null) return value
  return Array.isArray(value) ? value.map(item => labelOf(options, item)) : labelOf(options, value)
}

/** One sent item → its option value (a value as is, else the option with that label), or the item unchanged. */
function valueOf(options: OptionLike[], item: unknown, above: string[] | null): unknown {
  if (typeof item !== 'string') return item
  if (options.some(option => option.value === item)) return item
  const wanted = item.trim().toLowerCase()
  const matches = options.filter(option => option.label.trim().toLowerCase() === wanted)
  const pick = matches.length > 1 && above ? (matches.find(option => option.parent !== undefined && above.includes(option.parent)) ?? matches[0]) : matches[0]
  return pick?.value ?? item
}

/**
 * Sent answers with labels turned into values, for every question with options. `fields` in form
 * order, so a level's choice above is already a value when the level is read.
 */
export function choicesIn(fields: FieldLike[], answers: Record<string, unknown>): Record<string, unknown> {
  const out = { ...answers }
  const keyOfId = new Map(fields.filter(field => field.id).map(field => [field.id!, field.key]))
  for (const field of fields) {
    const options = field.options ?? []
    if (!options.length || out[field.key] == null) continue
    const parentKey = field.option_parent ? keyOfId.get(field.option_parent) : undefined
    const raw = parentKey ? out[parentKey] : undefined
    const above = parentKey ? (Array.isArray(raw) ? raw.map(String) : raw != null ? [String(raw)] : []) : null
    const value = out[field.key]
    out[field.key] = Array.isArray(value) ? value.map(item => valueOf(options, item, above)) : valueOf(options, value, above)
  }
  return out
}

/** A GET filter's wanted text → the option value it names (label or value), else the text. */
export const choiceFilter = (field: FieldLike, wanted: string): string => {
  const value = valueOf(field.options ?? [], wanted, null)
  return typeof value === 'string' ? value : wanted
}

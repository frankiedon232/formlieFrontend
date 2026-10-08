/**
 * Large dynamic lists on the server (F15 M5, owner 2026-10-08). A list switched to Large keeps its
 * options here: forms store the list's current options in their schema on the server (so submission
 * checks, the API service, exports and labels work as for any list), but they never leave the server.
 * Every reply goes through `trimLargeLists`, which leaves them out and says how many there are and which
 * choices one level up have options under them. Browsers ask for options as people type
 * (`lookupOptions` in shared/utils/forms/options.ts).
 */
import type { OptionList } from '#shared/types/forms'
import { allFields, type FormField } from '#shared/utils/forms/build'
import { LARGE_LIST_TYPES, keptOnServer, offeredOptions } from '#shared/utils/forms/options'
import type { FormSchemaV1 } from '#shared/utils/forms/schema'

const isLargeType = (type: string) => (LARGE_LIST_TYPES as readonly string[]).includes(type)

/**
 * Fields filled from lists kept on the server (large, or above 20 options) get the list's current options (and a dropdown / multi-select when they
 * were something else); fields whose list is no longer large keep a copy as before. Returns how many changed.
 */
export function fillLargeLists(schema: FormSchemaV1 | null | undefined, lists: OptionList[], only?: string): number {
  if (!schema) return 0
  const byId = new Map(lists.map(list => [list.id, list]))
  let changed = 0
  for (const field of allFields(schema)) {
    if (!field.option_set_id || (only && field.option_set_id !== only)) continue
    const list = byId.get(field.option_set_id)
    if (list && keptOnServer(list)) {
      field.options = offeredOptions(list, field.option_level ?? 0)
      field.options_large = { total: field.options.length }
      if (!isLargeType(field.type)) field.type = field.type === 'checkbox' ? 'multi_select' : 'dropdown'
      changed++
    } else if (field.options_large) {
      if (list) field.options = offeredOptions(list, field.option_level ?? 0)
      delete field.options_large
      changed++
    }
  }
  return changed
}

/** A field without its large list's options: how many, and the choices above that have options under them. */
function trimField(field: Record<string, unknown>): Record<string, unknown> {
  const options = field.options as { parent?: string }[]
  const parents = [...new Set(options.flatMap(option => (option.parent !== undefined ? [option.parent] : [])))]
  return { ...field, options: [], options_large: { total: options.length, ...(field.option_parent ? { parents } : {}) } }
}

/** Any reply with large lists' options left out (copies only what changes; `partial` sets are kept). */
export function trimLargeLists<T>(value: T): T {
  if (Array.isArray(value)) {
    let changed = false
    const out = value.map(item => {
      const next = trimLargeLists(item)
      if (next !== item) changed = true
      return next
    })
    return (changed ? out : value) as T
  }
  if (value && typeof value === 'object') {
    const record = value as Record<string, unknown>
    const large = record.options_large as { partial?: boolean } | null | undefined
    if (large && !large.partial && Array.isArray(record.options) && record.options.length) return trimField(record) as T
    let changed = false
    const out: Record<string, unknown> = {}
    for (const [key, item] of Object.entries(record)) {
      const next = trimLargeLists(item)
      if (next !== item) changed = true
      out[key] = next
    }
    return (changed ? out : value) as T
  }
  return value
}

/**
 * A schema for showing answers (responses, F15 M5): large lists keep only the options that were
 * answered, so labels read as usual without sending the whole list.
 */
export function keepAnswered<S extends FormSchemaV1 | null>(schema: S, answers: Record<string, unknown>[]): S {
  if (!schema || !allFields(schema).some(field => field.options_large)) return schema
  const copy = { ...schema, pages: schema.pages.map(page => ({ ...page, rows: page.rows.map(row => ({ ...row, fields: row.fields.map(field => (field.options_large ? answeredOnly(field, answers) : field)) })) })) }
  return copy as S
}
function answeredOnly(field: FormField, answers: Record<string, unknown>[]): FormField {
  const used = new Set(answers.flatMap(data => [data[field.key]].flat()).filter((value): value is string => typeof value === 'string'))
  const options = (field.options ?? []).filter(option => used.has(option.value))
  return { ...field, options, options_large: { total: field.options_large?.total ?? field.options?.length ?? 0, partial: true } }
}

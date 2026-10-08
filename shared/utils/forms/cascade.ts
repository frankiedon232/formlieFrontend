/**
 * Lists with levels in forms (F15 M2, owner 2026-10-07: "what you select matches and drops down; if it
 * doesn't match it doesn't drop"). A level field (`option_parent` = the field one level up) offers only
 * the options under what was chosen above (`option.parent`); it opens only when there are some, and a
 * closed level is not asked (not required, its answer dropped). Each level may allow one or several
 * choices; several chosen above → the options under any of them. The renderer and the server use the
 * same rules, so what people see is what gets checked.
 */
import type { FormField } from './build'
import { MAX_LIST_LEVELS } from './options'

type Option = NonNullable<FormField['options']>[number]
type FieldsById = Map<string, FormField>

/** A field from a large list in the browser (F15 M5): its options stay on the server. */
const remoteLevel = (field: FormField) => !!field.options_large && !field.options?.length

const chosen = (value: unknown): string[] => (Array.isArray(value) ? value.filter((item): item is string => typeof item === 'string') : typeof value === 'string' && value ? [value] : [])

/** The options a field offers with these answers (all of them for fields without a level above). */
export function cascadeOptions(field: FormField, fieldsById: FieldsById, answers: Record<string, unknown>, depth = 0): Option[] {
  const options = field.options ?? []
  if (!field.option_parent || depth > MAX_LIST_LEVELS) return options
  const parent = fieldsById.get(field.option_parent)
  if (!parent) return options
  // A level above that is closed closes this one too
  if (cascadeClosed(parent, fieldsById, answers, depth + 1)) return []
  const above = chosen(answers[parent.key])
  return above.length ? options.filter(option => option.parent !== undefined && above.includes(option.parent)) : []
}

/** A level that has nothing to offer right now: hidden, not required, its answer dropped. */
export function cascadeClosed(field: FormField, fieldsById: FieldsById, answers: Record<string, unknown>, depth = 0): boolean {
  if (!field.option_parent || depth > MAX_LIST_LEVELS) return false
  if (!remoteLevel(field)) return cascadeOptions(field, fieldsById, answers, depth).length === 0
  // Large list: open when a choice above has options under it (the server says which do)
  const parent = fieldsById.get(field.option_parent)
  if (!parent) return false
  if (cascadeClosed(parent, fieldsById, answers, depth + 1)) return true
  const above = chosen(answers[parent.key])
  // Not known yet (a field just added in the builder): open as soon as something is chosen above
  const known = field.options_large?.parents
  if (!known) return !above.length
  const open = new Set(known)
  return !above.some(value => open.has(value))
}

/** The answer kept to what the field offers now (a changed choice above clears what no longer fits). */
export function fitAnswer(field: FormField, fieldsById: FieldsById, answers: Record<string, unknown>): unknown {
  const value = answers[field.key]
  // A large list's level is fitted by the page as the choice above changes, and checked by the server
  if (!field.option_parent || value == null || remoteLevel(field)) return value
  const allowed = new Set(cascadeOptions(field, fieldsById, answers).map(option => option.value))
  if (Array.isArray(value)) {
    const kept = value.filter(item => typeof item === 'string' && allowed.has(item))
    return kept.length === value.length ? value : kept.length ? kept : undefined
  }
  return typeof value === 'string' && allowed.has(value) ? value : undefined
}

/** The fields of a chain, top first, from any one of them. */
export function cascadeChain(field: FormField, fields: FormField[]): FormField[] {
  const byId = new Map(fields.map(item => [item.id, item]))
  let top = field
  for (let i = 0; i < MAX_LIST_LEVELS && top.option_parent && byId.get(top.option_parent); i++) top = byId.get(top.option_parent)!
  const chain = [top]
  for (let i = 1; i < MAX_LIST_LEVELS; i++) {
    const child = fields.find(item => item.option_parent === chain.at(-1)!.id)
    if (!child) break
    chain.push(child)
  }
  return chain
}

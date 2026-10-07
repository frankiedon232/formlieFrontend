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

const chosen = (value: unknown): string[] => (Array.isArray(value) ? value.filter((item): item is string => typeof item === 'string') : typeof value === 'string' && value ? [value] : [])

/** The options a field offers with these answers (all of them for fields without a level above). */
export function cascadeOptions(field: FormField, fieldsById: FieldsById, answers: Record<string, unknown>, depth = 0): Option[] {
  const options = field.options ?? []
  if (!field.option_parent || depth > MAX_LIST_LEVELS) return options
  const parent = fieldsById.get(field.option_parent)
  if (!parent) return options
  // A level above that is closed closes this one too
  if (parent.option_parent && !cascadeOptions(parent, fieldsById, answers, depth + 1).length) return []
  const above = chosen(answers[parent.key])
  return above.length ? options.filter(option => option.parent !== undefined && above.includes(option.parent)) : []
}

/** A level that has nothing to offer right now: hidden, not required, its answer dropped. */
export const cascadeClosed = (field: FormField, fieldsById: FieldsById, answers: Record<string, unknown>) =>
  !!field.option_parent && cascadeOptions(field, fieldsById, answers).length === 0

/** The answer kept to what the field offers now (a changed choice above clears what no longer fits). */
export function fitAnswer(field: FormField, fieldsById: FieldsById, answers: Record<string, unknown>): unknown {
  const value = answers[field.key]
  if (!field.option_parent || value == null) return value
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

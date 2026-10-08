/**
 * Details and auto-fill (F15 M4): options of a list may carry details (`attrs`, the list's columns such
 * as postcode, price, manager). A one-choice field (`props.fills = [{ column, target, lock }]`) fills
 * other fields from the chosen option's details:
 * - lock: the target always shows the detail and can't be changed (also when nothing is chosen: empty);
 * - not locked: the target is filled while it is empty or still holds a filled-in detail, so a person's
 *   own typing is never overwritten.
 * Runs inside the logic engine, so the form page and the server fill alike (a locked value can't be faked).
 */
import type { FormField } from './build'

export interface FieldFill {
  column: string
  target: string
  lock?: boolean
}
type Attr = string | number
type FillState = { values: Map<string, string | number | null | string[]>; disabled: Set<string>; enabled: Set<string> }

/** A field's valid fills. */
export function fillsOf(field: Pick<FormField, 'props'>): FieldFill[] {
  const raw = field.props?.fills
  if (!Array.isArray(raw)) return []
  return raw.filter((item): item is FieldFill => !!item && typeof item === 'object' && typeof (item as FieldFill).column === 'string' && typeof (item as FieldFill).target === 'string')
}

const attrsOf = (option: unknown): Record<string, Attr> | undefined => (option as { attrs?: Record<string, Attr> } | undefined)?.attrs

/** The detail as the target field takes it (numbers for number questions). */
function valueFor(target: FormField, attr: Attr): string | number {
  if (['number', 'currency', 'percentage', 'slider'].includes(target.type)) {
    const n = typeof attr === 'number' ? attr : Number(String(attr).replace(',', '.'))
    return Number.isFinite(n) ? n : String(attr)
  }
  return String(attr)
}

/** Options the page learned from the server for fields whose list stays there (by field id). */
export type PickedOptions = Record<string, { value: string; label: string; attrs?: Record<string, Attr> }[]>

export function applyFills(state: FillState, fields: FormField[], answers: Record<string, unknown>, picked?: PickedOptions) {
  const byId = new Map(fields.map(field => [field.id, field]))
  for (const source of fields) {
    const fills = fillsOf(source)
    if (!fills.length) continue
    const options = source.options?.length ? source.options : (picked?.[source.id] ?? [])
    const chosen = answers[source.key]
    const option = typeof chosen === 'string' ? options.find(item => item.value === chosen) : undefined
    for (const fill of fills) {
      const target = byId.get(fill.target)
      if (!target || target.id === source.id) continue
      const attr = attrsOf(option)?.[fill.column]
      const value = attr === undefined || attr === '' ? null : valueFor(target, attr)
      if (fill.lock) {
        state.disabled.add(target.id)
        state.enabled.delete(target.id)
        state.values.set(target.id, value)
        continue
      }
      const current = answers[target.key]
      const filled = new Set(options.map(item => attrsOf(item)?.[fill.column]).filter(item => item !== undefined && item !== '').map(String))
      const untouched = current == null || current === '' || filled.has(String(current))
      if (untouched && (value !== null || filled.has(String(current)))) state.values.set(target.id, value)
    }
  }
}

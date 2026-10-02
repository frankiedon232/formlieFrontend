/**
 * Form logic (FormSchema v1 `logic`) — one evaluator for the builder preview, the public form
 * and the API.
 *
 *   rule = { id, when: { all | any: [{ field, op, value?, value2? }] }, then: [{ action, target?, value? }] }
 *
 * Conditions test answers (field ids, not keys). Actions: show / hide a field or a page,
 * require / make optional, enable / disable, set / clear a value, jump to a page, skip to the end.
 * Calculated fields: see ./formula.ts.
 */
import type { FormField } from './build'
import type { FormSchemaV1 } from './schema'

export type LogicOperator =
  | 'eq' | 'neq' | 'contains' | 'not_contains' | 'starts_with' | 'ends_with'
  | 'empty' | 'not_empty'
  | 'gt' | 'gte' | 'lt' | 'lte' | 'between' | 'not_between'
  | 'in' | 'not_in' | 'contains_all' | 'count_gte' | 'count_lte'
  | 'true' | 'false' | 'before' | 'after'

export type LogicAction =
  | 'show' | 'hide' | 'show_page' | 'hide_page'
  | 'require' | 'unrequire' | 'enable' | 'disable'
  | 'set_value' | 'clear_value' | 'jump' | 'skip_to_end'

export type LogicValue = string | number | null | string[]

export interface LogicCondition {
  field: string
  op: LogicOperator
  value?: LogicValue
  /** Upper bound for between / not between. */
  value2?: string | number | null
}
export interface LogicEffect {
  action: LogicAction
  /** Field id, or page id for show_page / hide_page / jump; none for skip_to_end. */
  target?: string
  /** For set_value. */
  value?: LogicValue
}
export interface LogicRule {
  id: string
  when: { all?: LogicCondition[]; any?: LogicCondition[] }
  then: LogicEffect[]
}

export type FieldKind = 'text' | 'number' | 'choice' | 'multi' | 'toggle' | 'date' | 'presence'
const KIND: Record<string, FieldKind> = {
  number: 'number', currency: 'number', rating: 'number', scale: 'number', slider: 'number', calculated: 'number',
  dropdown: 'choice', radio: 'choice', country: 'choice',
  multi_select: 'multi', checkbox: 'multi', ranking: 'multi',
  toggle: 'toggle',
  date: 'date', datetime: 'date', time: 'date',
  file_upload: 'presence', image_upload: 'presence', signature: 'presence', address: 'presence',
  matrix: 'presence', date_range: 'presence',
}
export const fieldKind = (type: string): FieldKind => KIND[type] ?? 'text'

/** Operators offered for a field type, in the order the editor shows them. */
export function operatorsFor(type: string): LogicOperator[] {
  switch (fieldKind(type)) {
    case 'number': return ['eq', 'neq', 'gt', 'gte', 'lt', 'lte', 'between', 'not_between', 'empty', 'not_empty']
    case 'choice': return ['eq', 'neq', 'in', 'not_in', 'empty', 'not_empty']
    case 'multi': return ['contains', 'not_contains', 'in', 'contains_all', 'count_gte', 'count_lte', 'empty', 'not_empty']
    case 'toggle': return ['true', 'false']
    case 'date': return ['eq', 'before', 'after', 'between', 'not_between', 'empty', 'not_empty']
    case 'presence': return ['not_empty', 'empty']
    default: return ['eq', 'neq', 'contains', 'not_contains', 'starts_with', 'ends_with', 'empty', 'not_empty']
  }
}
export const needsValue = (op: LogicOperator) => !['empty', 'not_empty', 'true', 'false'].includes(op)
/** Operators whose value is a list of options. */
export const takesList = (op: LogicOperator) => ['in', 'not_in', 'contains_all'].includes(op)
export const takesRange = (op: LogicOperator) => op === 'between' || op === 'not_between'
export const takesCount = (op: LogicOperator) => op === 'count_gte' || op === 'count_lte'

/** Actions and what they point at. */
export const LOGIC_ACTIONS: { action: LogicAction; target: 'field' | 'input' | 'page' | 'none'; icon: string }[] = [
  { action: 'show', target: 'field', icon: 'i-lucide-eye' },
  { action: 'hide', target: 'field', icon: 'i-lucide-eye-off' },
  { action: 'require', target: 'input', icon: 'i-lucide-asterisk' },
  { action: 'unrequire', target: 'input', icon: 'i-lucide-circle-slash' },
  { action: 'enable', target: 'input', icon: 'i-lucide-unlock' },
  { action: 'disable', target: 'input', icon: 'i-lucide-lock' },
  { action: 'set_value', target: 'input', icon: 'i-lucide-pen-line' },
  { action: 'clear_value', target: 'input', icon: 'i-lucide-eraser' },
  { action: 'show_page', target: 'page', icon: 'i-lucide-file-check' },
  { action: 'hide_page', target: 'page', icon: 'i-lucide-file-x' },
  { action: 'jump', target: 'page', icon: 'i-lucide-corner-down-right' },
  { action: 'skip_to_end', target: 'none', icon: 'i-lucide-flag' },
]
export const actionTarget = (action: LogicAction) => LOGIC_ACTIONS.find(a => a.action === action)?.target ?? 'field'

const isEmpty = (v: unknown) =>
  v == null || v === '' || v === false ||
  (Array.isArray(v) && !v.length) ||
  (typeof v === 'object' && !Array.isArray(v) && !(v instanceof Blob) && !Object.values(v as object).some(x => x != null && x !== ''))

const toNumber = (v: unknown) => (v == null || v === '' ? NaN : Number(v))
const list = (v: LogicValue | undefined) => (Array.isArray(v) ? v.map(String) : v == null || v === '' ? [] : [String(v)])

function test(condition: LogicCondition, answer: unknown): boolean {
  const { op, value, value2 } = condition
  if (op === 'empty') return isEmpty(answer)
  if (op === 'not_empty') return !isEmpty(answer)
  if (op === 'true') return answer === true
  if (op === 'false') return answer !== true

  // Lists: multi-select / checkbox / ranking answers.
  if (Array.isArray(answer)) {
    const chosen = answer.map(String)
    const wanted = list(value)
    if (op === 'contains' || op === 'eq') return chosen.includes(String(value))
    if (op === 'not_contains' || op === 'neq') return !chosen.includes(String(value))
    if (op === 'in') return wanted.some(w => chosen.includes(w))
    if (op === 'not_in') return !wanted.some(w => chosen.includes(w))
    if (op === 'contains_all') return wanted.length > 0 && wanted.every(w => chosen.includes(w))
    if (op === 'count_gte') return chosen.length >= Number(value)
    if (op === 'count_lte') return chosen.length <= Number(value)
    return false
  }
  if (op === 'in') return list(value).includes(String(answer ?? ''))
  if (op === 'not_in') return !list(value).includes(String(answer ?? ''))

  // Dates (ISO text compares correctly as text).
  if (op === 'before' || op === 'after') {
    if (typeof answer !== 'string' || !answer || !value) return false
    return op === 'before' ? answer < String(value) : answer > String(value)
  }

  if (['gt', 'gte', 'lt', 'lte', 'between', 'not_between'].includes(op)) {
    const isDate = typeof answer === 'string' && /^\d{4}-\d{2}-\d{2}/.test(answer)
    if (isEmpty(answer)) return false
    if (takesRange(op)) {
      const inside = isDate
        ? (!value || String(answer) >= String(value)) && (!value2 || String(answer) <= String(value2))
        : (value == null || value === '' || toNumber(answer) >= toNumber(value)) &&
          (value2 == null || value2 === '' || toNumber(answer) <= toNumber(value2))
      return op === 'between' ? inside : !inside
    }
    const a = toNumber(answer)
    const b = toNumber(value)
    if (Number.isNaN(a) || Number.isNaN(b)) return false
    return op === 'gt' ? a > b : op === 'gte' ? a >= b : op === 'lt' ? a < b : a <= b
  }

  const text = answer == null ? '' : String(answer).toLowerCase()
  const expected = value == null ? '' : String(value).toLowerCase()
  if (op === 'contains') return text.includes(expected)
  if (op === 'not_contains') return !text.includes(expected)
  if (op === 'starts_with') return text.startsWith(expected)
  if (op === 'ends_with') return text.endsWith(expected)
  if (op === 'eq') return text === expected
  if (op === 'neq') return text !== expected
  return false
}

/** Does the rule's condition hold? `answers` are keyed by field key; conditions use field ids. */
export function ruleMatches(rule: LogicRule, answers: Record<string, unknown>, keyOf: (id: string) => string | undefined) {
  const check = (c: LogicCondition) => {
    const key = keyOf(c.field)
    return key !== undefined && test(c, answers[key])
  }
  if (rule.when.any?.length) return rule.when.any.some(check)
  if (rule.when.all?.length) return rule.when.all.every(check)
  return false
}

export const END_OF_FORM = '__end__'

export interface LogicState {
  hidden: Set<string>
  hiddenPages: Set<string>
  required: Set<string>
  optional: Set<string>
  disabled: Set<string>
  enabled: Set<string>
  /** Field id → value to set (null = clear). Last matching rule wins. */
  values: Map<string, LogicValue>
  /** Page id → page id to go to next (or END_OF_FORM). First matching rule wins. */
  jumps: Map<string, string>
}

/**
 * The current effect of all rules.
 * - "show" (field or page) hides its target until the rule matches; "hide" hides it while it matches.
 * - Jumps and "skip to end" apply on the page that holds the rule's first condition field.
 */
export function evaluateLogic(schema: FormSchemaV1, answers: Record<string, unknown>): LogicState {
  const rules = (schema.logic ?? []) as LogicRule[]
  const fields = new Map<string, { field: FormField; page: string }>()
  for (const page of schema.pages) for (const row of page.rows) for (const field of row.fields) fields.set(field.id, { field, page: page.id })
  const keyOf = (id: string) => fields.get(id)?.field.key
  const state: LogicState = {
    hidden: new Set(), hiddenPages: new Set(), required: new Set(), optional: new Set(),
    disabled: new Set(), enabled: new Set(), values: new Map(), jumps: new Map(),
  }

  for (const rule of rules) {
    const match = ruleMatches(rule, answers, keyOf)
    for (const effect of rule.then) {
      const target = effect.target ?? ''
      switch (effect.action) {
        case 'show': if (!match) state.hidden.add(target); break
        case 'hide': if (match) state.hidden.add(target); break
        case 'show_page': if (!match) state.hiddenPages.add(target); break
        case 'hide_page': if (match) state.hiddenPages.add(target); break
        case 'require': if (match) state.required.add(target); break
        case 'unrequire': if (match) state.optional.add(target); break
        case 'enable': if (match) state.enabled.add(target); break
        case 'disable': if (match) state.disabled.add(target); break
        case 'set_value': if (match) state.values.set(target, effect.value ?? null); break
        case 'clear_value': if (match) state.values.set(target, null); break
        case 'jump':
        case 'skip_to_end': {
          if (!match) break
          const first = rule.when.all?.[0] ?? rule.when.any?.[0]
          const from = first ? fields.get(first.field)?.page : undefined
          if (from && !state.jumps.has(from)) state.jumps.set(from, effect.action === 'jump' ? target : END_OF_FORM)
        }
      }
    }
  }
  return state
}

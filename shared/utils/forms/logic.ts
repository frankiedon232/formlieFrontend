/**
 * Form logic (FormSchema v1 `logic`) — one evaluator for the builder preview, the public form
 * and the API: show / hide fields, required-if, jump to a page, plus calculated fields
 * (a tiny arithmetic parser — never `eval`).
 *
 *   rule = { id, when: { all | any: [{ field, op, value }] }, then: [{ action, target }] }
 */
import type { FormField } from './build'
import type { FormSchemaV1 } from './schema'

export type LogicOperator =
  | 'eq' | 'neq' | 'contains' | 'not_contains' | 'empty' | 'not_empty'
  | 'gt' | 'gte' | 'lt' | 'lte' | 'true' | 'false' | 'before' | 'after'
export type LogicAction = 'show' | 'hide' | 'require' | 'jump'

export interface LogicCondition {
  field: string
  op: LogicOperator
  value?: string | number | null
}
export interface LogicRule {
  id: string
  when: { all?: LogicCondition[]; any?: LogicCondition[] }
  then: { action: LogicAction; target: string }[]
}

type FieldKind = 'text' | 'number' | 'choice' | 'multi' | 'toggle' | 'date'
const KIND: Record<string, FieldKind> = {
  number: 'number', currency: 'number', rating: 'number', scale: 'number', slider: 'number', calculated: 'number',
  dropdown: 'choice', radio: 'choice', country: 'choice',
  multi_select: 'multi', checkbox: 'multi', ranking: 'multi',
  toggle: 'toggle',
  date: 'date', datetime: 'date',
}
export const fieldKind = (type: string): FieldKind => KIND[type] ?? 'text'

/** Operators offered for a field type, in the order the editor shows them. */
export function operatorsFor(type: string): LogicOperator[] {
  switch (fieldKind(type)) {
    case 'number': return ['eq', 'neq', 'gt', 'gte', 'lt', 'lte', 'empty', 'not_empty']
    case 'choice': return ['eq', 'neq', 'empty', 'not_empty']
    case 'multi': return ['contains', 'not_contains', 'empty', 'not_empty']
    case 'toggle': return ['true', 'false']
    case 'date': return ['eq', 'before', 'after', 'empty', 'not_empty']
    default: return ['eq', 'neq', 'contains', 'not_contains', 'empty', 'not_empty']
  }
}
export const needsValue = (op: LogicOperator) => !['empty', 'not_empty', 'true', 'false'].includes(op)

const isEmpty = (v: unknown) => v == null || v === '' || (Array.isArray(v) && !v.length) || (typeof v === 'object' && !Array.isArray(v) && !Object.keys(v as object).length)

function test(condition: LogicCondition, answer: unknown): boolean {
  const { op, value } = condition
  if (op === 'empty') return isEmpty(answer)
  if (op === 'not_empty') return !isEmpty(answer)
  if (op === 'true') return answer === true
  if (op === 'false') return answer !== true
  if (Array.isArray(answer)) {
    const has = answer.map(String).includes(String(value))
    return op === 'contains' || op === 'eq' ? has : op === 'not_contains' || op === 'neq' ? !has : false
  }
  if (op === 'before' || op === 'after') {
    if (typeof answer !== 'string' || !answer || !value) return false
    return op === 'before' ? answer < String(value) : answer > String(value)
  }
  if (['gt', 'gte', 'lt', 'lte'].includes(op)) {
    const a = Number(answer)
    const b = Number(value)
    if (Number.isNaN(a) || Number.isNaN(b) || isEmpty(answer)) return false
    return op === 'gt' ? a > b : op === 'gte' ? a >= b : op === 'lt' ? a < b : a <= b
  }
  const text = answer == null ? '' : String(answer).toLowerCase()
  const expected = value == null ? '' : String(value).toLowerCase()
  if (op === 'contains') return text.includes(expected)
  if (op === 'not_contains') return !text.includes(expected)
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

export interface LogicState {
  hidden: Set<string>
  required: Set<string>
  /** Page id to jump to after a given page id (first matching rule wins). */
  jumps: Map<string, string>
}

/**
 * The current effect of all rules. "show" rules hide their target until they match;
 * "hide" rules hide it while they match. Jump rules apply on the page that holds their
 * first condition's field.
 */
export function evaluateLogic(schema: FormSchemaV1, answers: Record<string, unknown>): LogicState {
  const rules = (schema.logic ?? []) as LogicRule[]
  const fields = new Map<string, { field: FormField; page: string }>()
  for (const page of schema.pages) for (const row of page.rows) for (const field of row.fields) fields.set(field.id, { field, page: page.id })
  const keyOf = (id: string) => fields.get(id)?.field.key
  const state: LogicState = { hidden: new Set(), required: new Set(), jumps: new Map() }

  for (const rule of rules) {
    const match = ruleMatches(rule, answers, keyOf)
    for (const effect of rule.then) {
      if (effect.action === 'show' && !match) state.hidden.add(effect.target)
      if (effect.action === 'hide' && match) state.hidden.add(effect.target)
      if (effect.action === 'require' && match) state.required.add(effect.target)
      if (effect.action === 'jump' && match) {
        const first = rule.when.all?.[0] ?? rule.when.any?.[0]
        const from = first ? fields.get(first.field)?.page : undefined
        if (from && !state.jumps.has(from)) state.jumps.set(from, effect.target)
      }
    }
  }
  return state
}

// ── Calculated fields ────────────────────────────────────────────────────────────────

/**
 * Evaluates `{quantity} * {price} + 5` safely: numbers, field keys in braces, + - * / ( ).
 * Returns null when the formula is invalid or uses a field without a number.
 */
export function calculate(formula: string, answers: Record<string, unknown>): number | null {
  const tokens = formula.match(/\{[a-z][a-z0-9_]*\}|\d+(?:\.\d+)?|[-+*/()]|\S/g) ?? []
  let i = 0
  const peek = () => tokens[i]
  const take = () => tokens[i++]

  function primary(): number {
    const token = take()
    if (token === undefined) throw new Error('end')
    if (token === '(') {
      const value = sum()
      if (take() !== ')') throw new Error('paren')
      return value
    }
    if (token === '-') return -primary()
    if (/^\d/.test(token)) return Number(token)
    if (token.startsWith('{')) {
      const raw = answers[token.slice(1, -1)]
      const value = typeof raw === 'number' ? raw : Number(raw)
      if (raw == null || raw === '' || Number.isNaN(value)) throw new Error('missing')
      return value
    }
    throw new Error(`token ${token}`)
  }
  function product(): number {
    let value = primary()
    while (peek() === '*' || peek() === '/') {
      const op = take()
      const right = primary()
      value = op === '*' ? value * right : value / right
    }
    return value
  }
  function sum(): number {
    let value = product()
    while (peek() === '+' || peek() === '-') {
      const op = take()
      const right = product()
      value = op === '+' ? value + right : value - right
    }
    return value
  }

  try {
    if (!tokens.length) return null
    const result = sum()
    if (i !== tokens.length || !Number.isFinite(result)) return null
    return Math.round(result * 1e6) / 1e6
  } catch {
    return null
  }
}

/** Field keys a formula refers to (to check they exist). */
export const formulaKeys = (formula: string) => [...formula.matchAll(/\{([a-z][a-z0-9_]*)\}/g)].map(m => m[1]!)

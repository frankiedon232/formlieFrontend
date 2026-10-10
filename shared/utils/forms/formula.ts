/**
 * Calculated fields, a small, safe formula language (never `eval`):
 *
 *   {quantity} * {unit_price}                       numbers, + - * / and brackets
 *   if({plan} = "premium", 50, 10)                  conditions: = != > >= < <=, "text" literals
 *   {size} + {extras}                               choice fields count as the number given to the
 *                                                   chosen option (several chosen → their sum)
 *   round(max({a}, {b}) * 1.2, 2)                   if and or not min max sum avg count round floor ceil abs
 *   avg({q1}, {q2}, {q3})                           sum / min / max / avg / count skip unanswered fields
 *   days({check_in}, {check_out})                   whole days between two dates (or date-times)
 *   if({score} >= 15, "High", "Low")                a calculation may also give a text (calculateResult)
 *   {product.price} * {quantity}                    a detail of the chosen list option (several: their sum;
 *                                                   leftovers L1, see ./details.ts)
 *
 * Returns null when the formula is invalid or needs an answer that is still missing.
 */
import type { FormField } from './build'
import { chosenDetails } from './details'
import type { PickedOptions } from './fills'

type Node =
  | { k: 'num'; v: number }
  | { k: 'str'; v: string }
  | { k: 'ref'; key: string; detail?: string }
  | { k: 'neg'; a: Node }
  | { k: 'bin'; op: string; a: Node; b: Node }
  | { k: 'call'; name: string; args: Node[] }

export const FORMULA_FUNCTIONS = ['if', 'and', 'or', 'not', 'min', 'max', 'sum', 'avg', 'count', 'days', 'round', 'floor', 'ceil', 'abs'] as const
const COMPARE = new Set(['=', '==', '!=', '<>', '>', '>=', '<', '<='])

function tokenize(formula: string): string[] {
  return formula.match(/\{[a-z][a-z0-9_]*(?:\.[a-z0-9_]+)?\}|\d+(?:\.\d+)?|"[^"]*"|'[^']*'|[a-z_]+|>=|<=|!=|==|<>|[-+*/(),=<>]|\S/gi) ?? []
}

/** Parses a formula into a tree; throws on any syntax error. */
export function parseFormula(formula: string): Node {
  const tokens = tokenize(formula)
  let i = 0
  const peek = () => tokens[i]
  const take = () => tokens[i++]
  const expect = (t: string) => {
    if (take() !== t) throw new Error(`expected ${t}`)
  }

  function primary(): Node {
    const token = take()
    if (token === undefined) throw new Error('end')
    if (token === '(') {
      const node = comparison()
      expect(')')
      return node
    }
    if (token === '-') return { k: 'neg', a: primary() }
    if (/^\d/.test(token)) return { k: 'num', v: Number(token) }
    if (/^["']/.test(token)) return { k: 'str', v: token.slice(1, -1) }
    if (token.startsWith('{')) {
      const [key, detail] = token.slice(1, -1).split('.')
      return detail ? { k: 'ref', key: key!, detail } : { k: 'ref', key: key! }
    }
    const name = token.toLowerCase()
    if ((FORMULA_FUNCTIONS as readonly string[]).includes(name) && peek() === '(') {
      take()
      const args: Node[] = []
      if (peek() !== ')') {
        args.push(comparison())
        while (peek() === ',') {
          take()
          args.push(comparison())
        }
      }
      expect(')')
      return { k: 'call', name, args }
    }
    throw new Error(`token ${token}`)
  }
  function product(): Node {
    let node = primary()
    while (peek() === '*' || peek() === '/') node = { k: 'bin', op: take()!, a: node, b: primary() }
    return node
  }
  function sum(): Node {
    let node = product()
    while (peek() === '+' || peek() === '-') node = { k: 'bin', op: take()!, a: node, b: product() }
    return node
  }
  function comparison(): Node {
    let node = sum()
    while (peek() !== undefined && COMPARE.has(peek()!)) node = { k: 'bin', op: take()!, a: node, b: sum() }
    return node
  }

  if (!tokens.length) throw new Error('empty')
  const tree = comparison()
  if (i !== tokens.length) throw new Error('trailing')
  return tree
}

export const isValidFormula = (formula: string) => {
  try {
    parseFormula(formula)
    return true
  } catch {
    return false
  }
}

/** A value inside the evaluator: its number (if it has one) and the texts it matches. */
interface Value {
  n: number | null
  s: string[]
  literal?: boolean
}
const num = (n: number): Value => ({ n, s: [String(n)] })
class Missing extends Error {}

function resolve(key: string, answers: Record<string, unknown>, fields?: Map<string, FormField>, detail?: string, picked?: PickedOptions): Value {
  const raw = answers[key]
  if (raw == null || raw === '' || (Array.isArray(raw) && !raw.length)) throw new Missing(key)
  const field = fields?.get(key)
  if (detail) {
    const details = field ? chosenDetails(field, raw, detail, picked) : null
    if (!details?.length) throw new Missing(key)
    const numbers = details.map(attr => (typeof attr === 'number' ? attr : Number(String(attr).replace(',', '.'))))
    return { n: numbers.every(Number.isFinite) ? numbers.reduce((sum, n) => sum + n, 0) : null, s: details.map(String) }
  }
  const options = field?.options ?? []
  const scored = options.some(o => typeof o.score === 'number')
  if (Array.isArray(raw)) {
    const chosen = options.filter(o => raw.map(String).includes(o.value))
    const n = scored ? chosen.reduce((total, o) => total + (o.score ?? 0), 0) : raw.length
    return { n, s: chosen.flatMap(o => [o.value, o.label]) }
  }
  if (options.length) {
    const option = options.find(o => o.value === String(raw))
    return { n: scored ? (option?.score ?? 0) : Number.isNaN(Number(raw)) ? null : Number(raw), s: option ? [option.value, option.label] : [String(raw)] }
  }
  if (typeof raw === 'boolean') return { n: raw ? 1 : 0, s: [String(raw)] }
  const n = typeof raw === 'number' ? raw : Number(raw)
  return { n: Number.isNaN(n) ? null : n, s: [String(raw)] }
}

function evaluate(node: Node, answers: Record<string, unknown>, fields?: Map<string, FormField>, picked?: PickedOptions): Value {
  const ev = (n: Node) => evaluate(n, answers, fields, picked)
  const number = (n: Node) => {
    const value = ev(n).n
    if (value === null) throw new Error('not a number')
    return value
  }
  /** Numbers of the answered arguments (unanswered ones are skipped). */
  const answered = (nodes: Node[]) =>
    nodes.flatMap(n => {
      try {
        const value = ev(n).n
        return value === null ? [] : [value]
      } catch (error) {
        if (error instanceof Missing) return []
        throw error
      }
    })
  const some = (nodes: Node[]) => {
    const values = answered(nodes)
    if (!values.length) throw new Missing('all')
    return values
  }
  switch (node.k) {
    case 'num': return num(node.v)
    case 'str': return { n: Number.isNaN(Number(node.v)) || node.v === '' ? null : Number(node.v), s: [node.v], literal: true }
    case 'ref': return resolve(node.key, answers, fields, node.detail, picked)
    case 'neg': return num(-number(node.a))
    case 'bin': {
      if (COMPARE.has(node.op)) {
        const a = ev(node.a)
        const b = ev(node.b)
        if (node.op === '=' || node.op === '==' || node.op === '!=' || node.op === '<>') {
          const textual = a.literal || b.literal || a.n === null || b.n === null
          const same = textual
            ? a.s.some(x => b.s.some(y => x.toLowerCase() === y.toLowerCase()))
            : a.n === b.n
          return num((node.op === '!=' || node.op === '<>') !== same ? 1 : 0)
        }
        if (a.n === null || b.n === null) throw new Error('not a number')
        const r = node.op === '>' ? a.n > b.n : node.op === '>=' ? a.n >= b.n : node.op === '<' ? a.n < b.n : a.n <= b.n
        return num(r ? 1 : 0)
      }
      const a = number(node.a)
      const b = number(node.b)
      return num(node.op === '+' ? a + b : node.op === '-' ? a - b : node.op === '*' ? a * b : a / b)
    }
    case 'call': {
      const args = node.args
      const truthy = (n: Node) => {
        const v = ev(n)
        return v.n !== null ? v.n !== 0 : v.s.some(s => s !== '' && s !== 'false')
      }
      switch (node.name) {
        case 'if':
          if (args.length !== 3) throw new Error('if needs 3')
          return truthy(args[0]!) ? ev(args[1]!) : ev(args[2]!)
        case 'and': return num(args.every(truthy) ? 1 : 0)
        case 'or': return num(args.some(truthy) ? 1 : 0)
        case 'not': return num(args[0] && truthy(args[0]) ? 0 : 1)
        case 'min': return num(Math.min(...some(args)))
        case 'max': return num(Math.max(...some(args)))
        case 'sum': return num(some(args).reduce((a, b) => a + b, 0))
        case 'avg': {
          const values = some(args)
          return num(values.reduce((a, b) => a + b, 0) / values.length)
        }
        case 'count': return num(answered(args).length)
        case 'days': {
          if (args.length !== 2) throw new Error('days needs 2')
          const [from, to] = args.map(n => Date.parse(String(ev(n).s[0] ?? '').slice(0, 10)))
          if (Number.isNaN(from) || Number.isNaN(to)) throw new Error('not a date')
          return num(Math.round((to! - from!) / 86_400_000))
        }
        case 'abs': return num(Math.abs(number(args[0]!)))
        case 'floor': return num(Math.floor(number(args[0]!)))
        case 'ceil': return num(Math.ceil(number(args[0]!)))
        case 'round': {
          const digits = args[1] ? Math.max(0, Math.min(10, number(args[1]))) : 0
          const f = 10 ** digits
          return num(Math.round(number(args[0]!) * f) / f)
        }
      }
    }
  }
  throw new Error('unknown')
}

/**
 * Evaluates a formula against the answers (by field key). `fields` (by key) lets choice fields use
 * the numbers given to their options.
 */
export function calculate(formula: string, answers: Record<string, unknown>, fields?: Map<string, FormField>, picked?: PickedOptions): number | null {
  const result = calculateResult(formula, answers, fields, picked)
  return typeof result === 'number' ? result : null
}

/** Like calculate, but a formula may also give a text, e.g. a risk level "High". */
export function calculateResult(
  formula: string,
  answers: Record<string, unknown>,
  fields?: Map<string, FormField>,
  picked?: PickedOptions,
): number | string | null {
  try {
    const value = evaluate(parseFormula(formula), answers, fields, picked)
    if (value.n === null) return value.literal && value.s[0] ? value.s[0] : null
    if (!Number.isFinite(value.n)) return null
    return Math.round(value.n * 1e6) / 1e6
  } catch {
    return null
  }
}

/** Field keys a formula refers to (to check they exist). */
export const formulaKeys = (formula: string) => [...formula.matchAll(/\{([a-z][a-z0-9_]*)(?:\.[a-z0-9_]+)?\}/g)].map(m => m[1]!)

/** Details a formula reads, as { key, detail } (to check the field's options carry them). */
export const formulaDetails = (formula: string) => [...formula.matchAll(/\{([a-z][a-z0-9_]*)\.([a-z0-9_]+)\}/g)].map(m => ({ key: m[1]!, detail: m[2]! }))

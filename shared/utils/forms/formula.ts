/**
 * Calculated fields — a small, safe formula language (never `eval`):
 *
 *   {quantity} * {unit_price}                       numbers, + - * / and brackets
 *   if({plan} = "premium", 50, 10)                  conditions: = != > >= < <=, "text" literals
 *   {size} + {extras}                               choice fields count as the number given to the
 *                                                   chosen option (several chosen → their sum)
 *   round(max({a}, {b}) * 1.2, 2)                   if and or not min max sum round floor ceil abs
 *
 * Returns null when the formula is invalid or needs an answer that is still missing.
 */
import type { FormField } from './build'

type Node =
  | { k: 'num'; v: number }
  | { k: 'str'; v: string }
  | { k: 'ref'; key: string }
  | { k: 'neg'; a: Node }
  | { k: 'bin'; op: string; a: Node; b: Node }
  | { k: 'call'; name: string; args: Node[] }

export const FORMULA_FUNCTIONS = ['if', 'and', 'or', 'not', 'min', 'max', 'sum', 'round', 'floor', 'ceil', 'abs'] as const
const COMPARE = new Set(['=', '==', '!=', '<>', '>', '>=', '<', '<='])

function tokenize(formula: string): string[] {
  return formula.match(/\{[a-z][a-z0-9_]*\}|\d+(?:\.\d+)?|"[^"]*"|'[^']*'|[a-z_]+|>=|<=|!=|==|<>|[-+*/(),=<>]|\S/gi) ?? []
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
    if (token.startsWith('{')) return { k: 'ref', key: token.slice(1, -1) }
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

function resolve(key: string, answers: Record<string, unknown>, fields?: Map<string, FormField>): Value {
  const raw = answers[key]
  if (raw == null || raw === '' || (Array.isArray(raw) && !raw.length)) throw new Missing(key)
  const field = fields?.get(key)
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

function evaluate(node: Node, answers: Record<string, unknown>, fields?: Map<string, FormField>): Value {
  const ev = (n: Node) => evaluate(n, answers, fields)
  const number = (n: Node) => {
    const value = ev(n).n
    if (value === null) throw new Error('not a number')
    return value
  }
  switch (node.k) {
    case 'num': return num(node.v)
    case 'str': return { n: Number.isNaN(Number(node.v)) || node.v === '' ? null : Number(node.v), s: [node.v], literal: true }
    case 'ref': return resolve(node.key, answers, fields)
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
        case 'min': return num(Math.min(...args.map(number)))
        case 'max': return num(Math.max(...args.map(number)))
        case 'sum': return num(args.map(number).reduce((a, b) => a + b, 0))
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
export function calculate(formula: string, answers: Record<string, unknown>, fields?: Map<string, FormField>): number | null {
  try {
    const value = evaluate(parseFormula(formula), answers, fields).n
    if (value === null || !Number.isFinite(value)) return null
    return Math.round(value * 1e6) / 1e6
  } catch {
    return null
  }
}

/** Field keys a formula refers to (to check they exist). */
export const formulaKeys = (formula: string) => [...formula.matchAll(/\{([a-z][a-z0-9_]*)\}/g)].map(m => m[1]!)

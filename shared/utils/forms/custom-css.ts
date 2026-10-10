/**
 * Custom CSS for a form (F8, leftovers L5, owner 2026-10-10), on plans that include it. Code written by a
 * customer runs on Formalie's pages, so it is cleaned the same way in the designer (to show what was taken out)
 * and on the server (what is stored and served), and fenced:
 *
 * - every selector is put inside the form box (`[data-form-css]`, the form's <main>); `:root`, `html` and
 *   `body` mean the box itself, so the page frame (organisation bar, "Secured by Formalie") can't be touched;
 *   the box also paints nothing outside itself (`contain: paint` on the page);
 * - kept: style rules, @media, @supports and @container around them;
 * - taken out: every other at-rule (@import, @font-face, @keyframes, @namespace …), anything that loads from
 *   elsewhere (url(), image-set(), src()), script-like values (expression(), javascript:, behavior,
 *   -moz-binding), backslash escapes (they hide all of those), `<` (it could end the style element) and
 *   fixed positioning.
 *
 * At most 20,000 characters and 500 rules. Never throws: what can't be kept is left out and listed.
 */

export const CUSTOM_CSS_MAX = 20_000
const MAX_RULES = 500
/** The form box every rule is fenced to. */
export const CSS_SCOPE = '[data-form-css]'
const BLOCK_AT_RULES = new Set(['media', 'supports', 'container'])

export type CssIssueKind = 'too_long' | 'too_many' | 'at_rule' | 'loads' | 'script' | 'escape' | 'html' | 'fixed' | 'syntax'
export interface CssIssue {
  kind: CssIssueKind
  /** The piece that was left out (shortened). */
  text: string
}

const short = (text: string) => (text.length > 60 ? `${text.slice(0, 57)}...` : text).replace(/\s+/g, ' ').trim()

/** Splits on a character outside brackets and strings. */
function splitTop(text: string, separator: string): string[] {
  const parts: string[] = []
  let depth = 0
  let quote: string | null = null
  let start = 0
  for (let i = 0; i < text.length; i++) {
    const c = text[i]!
    if (quote) {
      if (c === quote) quote = null
    } else if (c === '"' || c === "'") quote = c
    else if (c === '(' || c === '[') depth++
    else if (c === ')' || c === ']') depth--
    else if (c === separator && depth === 0) {
      parts.push(text.slice(start, i))
      start = i + 1
    }
  }
  parts.push(text.slice(start))
  return parts
}

/** The index of the `}` closing the block that opens at `open` (strings respected), or -1. */
function closing(text: string, open: number): number {
  let depth = 0
  let quote: string | null = null
  for (let i = open; i < text.length; i++) {
    const c = text[i]!
    if (quote) {
      if (c === quote) quote = null
    } else if (c === '"' || c === "'") quote = c
    else if (c === '{') depth++
    else if (c === '}' && --depth === 0) return i
  }
  return -1
}

const LOADS = /\b(?:url|image-set|-webkit-image-set|src|image)\s*\(/i
const SCRIPT = /expression\s*\(|javascript:|vbscript:|data:\s*text\/html/i
const SCRIPT_PROPERTY = /^(?:behavior|-moz-binding|-ms-behavior)$/i
const PROPERTY = /^(?:--[\w-]+|-?[a-z][a-z0-9-]*)$/i

/** One selector put inside the form box. */
function fence(selector: string): string {
  const s = selector.trim()
  const root = /^(?::root|html|body)(?![\w-])/i.exec(s)
  if (root) {
    const rest = s.slice(root[0].length).replace(/^\s*(?:body(?![\w-]))?/i, '')
    return `${CSS_SCOPE}${rest}`
  }
  return `${CSS_SCOPE} ${s}`
}

interface State {
  issues: CssIssue[]
  rules: number
}

function cleanDeclarations(body: string, state: State): string {
  const kept: string[] = []
  for (const raw of splitTop(body, ';')) {
    const declaration = raw.trim()
    if (!declaration) continue
    const colon = declaration.indexOf(':')
    if (colon < 1) {
      state.issues.push({ kind: 'syntax', text: short(declaration) })
      continue
    }
    const property = declaration.slice(0, colon).trim()
    const value = declaration.slice(colon + 1).trim()
    if (!PROPERTY.test(property)) state.issues.push({ kind: 'syntax', text: short(declaration) })
    else if (SCRIPT_PROPERTY.test(property) || SCRIPT.test(value)) state.issues.push({ kind: 'script', text: short(declaration) })
    else if (LOADS.test(value)) state.issues.push({ kind: 'loads', text: short(declaration) })
    else if (/^position$/i.test(property) && /\bfixed\b/i.test(value)) state.issues.push({ kind: 'fixed', text: short(declaration) })
    else kept.push(`${property.toLowerCase()}: ${value}`)
  }
  return kept.join('; ')
}

function cleanSheet(text: string, state: State, depth: number): string {
  const out: string[] = []
  let i = 0
  while (i < text.length) {
    const open = text.indexOf('{', i)
    const semicolon = text.indexOf(';', i)
    // A statement at-rule (@import url(...); @charset ...;) ends at a semicolon before any block
    if (semicolon >= 0 && (open < 0 || semicolon < open)) {
      const statement = text.slice(i, semicolon).trim()
      if (statement) state.issues.push({ kind: /^@import/i.test(statement) ? 'loads' : statement.startsWith('@') ? 'at_rule' : 'syntax', text: short(statement) })
      i = semicolon + 1
      continue
    }
    if (open < 0) {
      if (text.slice(i).trim()) state.issues.push({ kind: 'syntax', text: short(text.slice(i)) })
      break
    }
    const end = closing(text, open)
    if (end < 0) {
      state.issues.push({ kind: 'syntax', text: short(text.slice(i)) })
      break
    }
    const prelude = text.slice(i, open).trim()
    const body = text.slice(open + 1, end)
    i = end + 1
    if (prelude.startsWith('@')) {
      const name = /^@([\w-]+)/.exec(prelude)?.[1]?.toLowerCase() ?? ''
      if (!BLOCK_AT_RULES.has(name) || depth > 2) state.issues.push({ kind: 'at_rule', text: short(prelude) })
      else if (LOADS.test(prelude) || SCRIPT.test(prelude)) state.issues.push({ kind: 'loads', text: short(prelude) })
      else {
        const inner = cleanSheet(body, state, depth + 1)
        if (inner) out.push(`${prelude.replace(/\s+/g, ' ')} {\n${inner}\n}`)
      }
      continue
    }
    if (++state.rules > MAX_RULES) {
      if (state.rules === MAX_RULES + 1) state.issues.push({ kind: 'too_many', text: short(prelude) })
      continue
    }
    const selectors = splitTop(prelude, ',').map(item => item.trim()).filter(Boolean)
    if (!selectors.length) {
      state.issues.push({ kind: 'syntax', text: short(`${prelude} {`) })
      continue
    }
    const declarations = cleanDeclarations(body, state)
    if (declarations) out.push(`${selectors.map(fence).join(', ')} { ${declarations} }`)
  }
  return out.join('\n')
}

/** Cleans custom CSS (see above): the CSS to store and serve, and what was left out. */
export function sanitiseCss(input: string | null | undefined): { css: string; issues: CssIssue[] } {
  const issues: CssIssue[] = []
  let text = String(input ?? '')
  if (!text.trim()) return { css: '', issues }
  if (text.length > CUSTOM_CSS_MAX) return { css: '', issues: [{ kind: 'too_long', text: String(text.length) }] }
  // Comments go first (they could hide anything); then the characters that are never needed
  text = text.replace(/\/\*[\s\S]*?(?:\*\/|$)/g, ' ')
  if (text.includes('\\')) {
    issues.push({ kind: 'escape', text: '\\' })
    // Escapes can spell anything ("u\72l(" is url(): rules holding one are dropped whole, below
    text = text.replace(/[^{};]*\\[^{};]*;?/g, '')
  }
  if (/[<]/.test(text)) {
    issues.push({ kind: 'html', text: '<' })
    text = text.replace(/</g, '')
  }
  const state: State = { issues, rules: 0 }
  const css = cleanSheet(text, state, 0)
  return { css, issues: state.issues }
}

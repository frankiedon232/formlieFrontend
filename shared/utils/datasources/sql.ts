/**
 * SQL text helpers for the Query editor (F12 M4), shared by the editor and the server: split a
 * script into statements (quotes, comments and dollar quotes respected), find the statement at the
 * cursor, tell what a statement does (reads, adds, changes, deletes, changes structure), the tables
 * it names, and its `:name` parameters (never `::casts`, never inside quotes).
 */

export type StatementKind = 'read' | 'insert' | 'update' | 'delete' | 'structure' | 'other'

export interface Statement {
  text: string
  /** Offsets in the script (the text without the closing semicolon). */
  from: number
  to: number
}

/** Each character's state: in code, or inside a quote / comment (whose text the helpers skip). */
function scan(sql: string, visit: (index: number, inCode: boolean) => void) {
  let i = 0
  while (i < sql.length) {
    const char = sql[i]!
    const next = sql[i + 1]
    if (char === '-' && next === '-') {
      const end = sql.indexOf('\n', i)
      const stop = end < 0 ? sql.length : end
      for (; i < stop; i++) visit(i, false)
      continue
    }
    if (char === '/' && next === '*') {
      const end = sql.indexOf('*/', i + 2)
      const stop = end < 0 ? sql.length : end + 2
      for (; i < stop; i++) visit(i, false)
      continue
    }
    if (char === "'" || char === '"' || char === '`' || char === '[') {
      const close = char === '[' ? ']' : char
      visit(i, false)
      i++
      while (i < sql.length) {
        visit(i, false)
        if (sql[i] === close) {
          if (sql[i + 1] === close && close !== ']') {
            visit(i + 1, false)
            i += 2
            continue
          }
          i++
          break
        }
        i++
      }
      continue
    }
    const dollar = char === '$' ? /^\$[A-Za-z_]*\$/.exec(sql.slice(i)) : null
    if (dollar) {
      const end = sql.indexOf(dollar[0], i + dollar[0].length)
      const stop = end < 0 ? sql.length : end + dollar[0].length
      for (; i < stop; i++) visit(i, false)
      continue
    }
    visit(i, true)
    i++
  }
}

/** The script's statements, in order (empty ones left out). */
export function splitStatements(sql: string): Statement[] {
  const out: Statement[] = []
  let start = 0
  scan(sql, (index, inCode) => {
    if (inCode && sql[index] === ';') {
      out.push({ text: sql.slice(start, index), from: start, to: index })
      start = index + 1
    }
  })
  out.push({ text: sql.slice(start), from: start, to: sql.length })
  return out
    .map(item => {
      const lead = item.text.length - item.text.trimStart().length
      const text = item.text.trim()
      return { text, from: item.from + lead, to: item.from + lead + text.length }
    })
    .filter(item => withoutComments(item.text).trim())
}

/** The statement the cursor is in (or right after); null on an empty script. */
export function statementAt(sql: string, cursor: number): Statement | null {
  const statements = splitStatements(sql)
  if (!statements.length) return null
  return statements.find(item => cursor >= item.from && cursor <= item.to + 1) ?? [...statements].reverse().find(item => item.from <= cursor) ?? statements[0]!
}

/** The text with comments blanked out and quoted parts kept as empty quotes. */
export function codeOnly(sql: string): string {
  let out = ''
  scan(sql, (index, inCode) => (out += inCode ? sql[index] : ' '))
  return out
}
const withoutComments = (sql: string) => sql.replace(/--[^\n]*/g, ' ').replace(/\/\*[\s\S]*?\*\//g, ' ')

/** What the statement does, from its words (a WITH that changes rows counts as that change). */
export function statementKind(sql: string): StatementKind {
  const code = codeOnly(sql).toUpperCase()
  const first = /^\s*\(?\s*([A-Z]+)/.exec(code)?.[1] ?? ''
  const change = (text: string): StatementKind | null => (/\bDELETE\b/.test(text) ? 'delete' : /\bUPDATE\b/.test(text) ? 'update' : /\b(INSERT|MERGE)\b/.test(text) ? 'insert' : null)
  if (first === 'WITH') return change(code) ?? 'read'
  if (['SELECT', 'SHOW', 'EXPLAIN', 'DESCRIBE', 'DESC', 'VALUES', 'TABLE'].includes(first)) return /\bINTO\b/.test(code) && first === 'SELECT' ? 'insert' : 'read'
  if (first === 'INSERT' || first === 'MERGE' || first === 'UPSERT' || first === 'REPLACE') return 'insert'
  if (first === 'UPDATE') return 'update'
  if (first === 'DELETE') return 'delete'
  if (['CREATE', 'ALTER', 'DROP', 'TRUNCATE', 'RENAME', 'COMMENT', 'GRANT', 'REVOKE'].includes(first)) return 'structure'
  return 'other'
}

/** Tables the statement names (after FROM, JOIN, UPDATE, INTO, TABLE), as written, quotes removed. */
export function tablesIn(sql: string): string[] {
  // Comments and string literals out; quoted names ("x", `x`, [x]) stay.
  const code = sql
    .replace(/--[^\n]*/g, ' ')
    .replace(/\/\*[\s\S]*?\*\//g, ' ')
    .replace(/'(?:[^']|'')*'/g, ' ')
  const names = [...code.matchAll(/\b(?:FROM|JOIN|UPDATE|INTO|TABLE)\s+((?:[\w$]+|"[^"]*"|`[^`]*`|\[[^\]]*\])(?:\s*\.\s*(?:[\w$]+|"[^"]*"|`[^`]*`|\[[^\]]*\]))?)/gi)]
  return [...new Set(names.map(match => match[1]!.replace(/\s/g, '').replace(/["`[\]]/g, '')))]
}

/** The `:name` parameters, in order of first use. */
export function parametersIn(sql: string): string[] {
  const code = codeOnly(sql)
  const out: string[] = []
  for (const match of code.matchAll(/(?<![:\w]):([A-Za-z_][\w]*)/g)) if (!out.includes(match[1]!)) out.push(match[1]!)
  return out
}

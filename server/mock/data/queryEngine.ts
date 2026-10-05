/**
 * The mock's SQL runner for the Query editor (F12 M4). Nothing connects to a database: it reads
 * the same tables and rows as the explorer and understands the common shapes,
 *
 *   SELECT cols | * | COUNT(*) · SUM · AVG · MIN · MAX [AS x] FROM table [WHERE … AND …] [GROUP BY …] [HAVING agg op n]
 *     [ORDER BY col / alias [DESC], …] [LIMIT n] [OFFSET m]
 *   INSERT INTO table (a, b) VALUES (…), (…)
 *   UPDATE table SET a = v, b = v [WHERE …]
 *   DELETE FROM table [WHERE …]
 *
 * (values: 'text', numbers, TRUE / FALSE, NULL, :parameters). Anything else answers with a
 * "preview" problem; the real backend runs any SQL the connection's account may run.
 */
import type { DatabaseTable } from '#shared/types/destinations'
import type { TableRow, TableStructure } from '#shared/types/explorer'
import type { QueryColumn } from '#shared/types/query'
import { parseValue } from '#shared/utils/datasources/values'
import { MockError } from '../core/respond'
import { changesOf, rowsOf, structureOf } from './databaseRows'
import type { StoredDataSource } from './dataSourceStore'
import type { MockTenant } from './tenants'

type Value = string | number | boolean | null

/** A database-style problem: its message (as a database words it) and where in the statement. */
export const sqlProblem = (message: string, position = 0) => new MockError('FRM-DEST-1025', [{ field: 'message', message }, { field: 'position', message: String(position) }])
const preview = () => new MockError('FRM-DEST-1025', [{ field: 'message', message: 'preview_unsupported' }, { field: 'position', message: '0' }])

/** Where a word starts in the statement, after it (for pointing at a line). */
const after = (statement: string, word: RegExp) => {
  const index = statement.search(word)
  return index < 0 ? 0 : index + (word.exec(statement)?.[0].length ?? 0)
}

const unquote = (name: string) => name.trim().replace(/^["`[]|["`\]]$/g, '')

export interface Resolved {
  tables: DatabaseTable[]
  table: DatabaseTable
  structure: TableStructure
}

/** `schema.table` or `table` (any schema the connection shows), case-insensitive. */
export function resolveTable(tenant: MockTenant, source: StoredDataSource, tables: DatabaseTable[], written: string, at: number): Resolved {
  const parts = written.split('.').map(unquote)
  const [schema, name] = parts.length > 1 ? [parts[0]!, parts[1]!] : [null, parts[0]!]
  const table = tables.find(item => item.name.toLowerCase() === name.toLowerCase() && (!schema || item.schema.toLowerCase() === schema.toLowerCase()))
  if (!table) throw sqlProblem(`relation "${written}" does not exist`, at)
  return { tables, table, structure: structureOf(tenant, source, tables, table) }
}

/** A literal or a :parameter. */
function valueOf(token: string, params: Record<string, string>, at: number): Value {
  const text = token.trim()
  if (/^'(?:[^']|'')*'$/.test(text)) return text.slice(1, -1).replace(/''/g, "'")
  if (/^-?\d+(\.\d+)?$/.test(text)) return Number(text)
  if (/^(TRUE|FALSE)$/i.test(text)) return /^TRUE$/i.test(text)
  if (/^NULL$/i.test(text)) return null
  const param = /^:([A-Za-z_]\w*)$/.exec(text)
  if (param) {
    if (!(param[1]! in params)) throw sqlProblem(`there is no value for parameter :${param[1]}`, at)
    return params[param[1]!] ?? null
  }
  throw sqlProblem(`syntax error at or near "${text.slice(0, 20)}"`, at)
}

/** Splits on a separator outside quotes and brackets. */
function splitOutside(text: string, separator: RegExp): string[] {
  const out: string[] = []
  let depth = 0
  let quote = false
  let start = 0
  for (let i = 0; i < text.length; i++) {
    const char = text[i]!
    if (char === "'") quote = !quote
    if (quote) continue
    if (char === '(') depth++
    if (char === ')') depth--
    if (depth === 0) {
      const match = separator.exec(text.slice(i))
      if (match && match.index === 0) {
        out.push(text.slice(start, i))
        i += match[0].length - 1
        start = i + 1
      }
    }
  }
  out.push(text.slice(start))
  return out.map(part => part.trim()).filter(Boolean)
}

const text = (value: unknown) => (value == null ? null : typeof value === 'object' ? JSON.stringify(value) : String(value))

/** A WHERE clause (conditions joined by AND) as a row test. */
function whereTest(clause: string | undefined, structure: TableStructure, params: Record<string, string>, at: number): (row: TableRow) => boolean {
  if (!clause) return () => true
  if (/\bOR\b/i.test(clause.replace(/'(?:[^']|'')*'/g, ''))) throw preview()
  const tests = splitOutside(clause, /^\s+AND\s+/i).map(condition => {
    const match = /^([\w."`[\]]+)\s*(=|!=|<>|>=|<=|>|<|NOT\s+LIKE|LIKE|NOT\s+ILIKE|ILIKE|IS\s+NOT\s+NULL|IS\s+NULL|NOT\s+IN|IN)\s*([\s\S]*)$/i.exec(condition)
    if (!match) throw sqlProblem(`syntax error at or near "${condition.slice(0, 20)}"`, at)
    const column = unquote(match[1]!.split('.').pop()!)
    const known = structure.columns.find(item => item.name.toLowerCase() === column.toLowerCase())
    if (!known) throw sqlProblem(`column "${column}" does not exist`, at)
    const op = match[2]!.toUpperCase().replace(/\s+/g, ' ')
    const rest = match[3]!.trim()
    if (op === 'IS NULL') return (row: TableRow) => row[known.name] == null
    if (op === 'IS NOT NULL') return (row: TableRow) => row[known.name] != null
    if (op === 'IN' || op === 'NOT IN') {
      const list = splitOutside(rest.replace(/^\(|\)$/g, ''), /^,/).map(item => text(valueOf(item, params, at)))
      return (row: TableRow) => list.includes(text(row[known.name])) === (op === 'IN')
    }
    const wanted = valueOf(rest, params, at)
    if (op.includes('LIKE')) {
      const pattern = new RegExp(`^${String(wanted).replace(/[.*+?^${}()|[\]\\]/g, '\\$&').replace(/%/g, '.*').replace(/_/g, '.')}$`, op.includes('ILIKE') ? 'i' : '')
      return (row: TableRow) => pattern.test(text(row[known.name]) ?? '') !== op.startsWith('NOT')
    }
    return (row: TableRow) => {
      const value = row[known.name]
      if (value == null || wanted == null) return false
      const [a, b] = typeof wanted === 'number' ? [Number(value), wanted] : [String(value), String(wanted)]
      return op === '=' ? a === b : op === '!=' || op === '<>' ? a !== b : op === '>' ? a > b : op === '<' ? a < b : op === '>=' ? a >= b : a <= b
    }
  })
  return row => tests.every(test => test(row))
}

export interface ReadResult {
  columns: QueryColumn[]
  rows: unknown[][]
}

export function runSelect(tenant: MockTenant, source: StoredDataSource, tables: DatabaseTable[], sql: string, params: Record<string, string>): ReadResult {
  const statement = sql.trim()
  // SELECT without FROM: the expressions themselves (SELECT 1, SELECT 'a' AS x)
  if (!/\bFROM\b/i.test(statement)) {
    const list = splitOutside(statement.replace(/^SELECT\s+/i, ''), /^,/)
    return {
      columns: list.map((item, index) => ({ name: /\s+AS\s+([\w"]+)$/i.exec(item)?.[1]?.replace(/"/g, '') ?? (list.length === 1 ? '?column?' : `column${index + 1}`), type: null })),
      rows: [list.map(item => valueOf(item.replace(/\s+AS\s+[\w"]+$/i, ''), params, 7))],
    }
  }
  const match = /^SELECT\s+(?:TOP\s+(\d+)\s+)?([\s\S]+?)\s+FROM\s+([\w."`[\]]+)(?:\s+(?:AS\s+)?(?!WHERE\b|GROUP\b|ORDER\b|LIMIT\b|OFFSET\b|FETCH\b|HAVING\b)\w+)?(?:\s+WHERE\s+([\s\S]+?))?(?:\s+GROUP\s+BY\s+([\s\S]+?))?(?:\s+HAVING\s+([\s\S]+?))?(?:\s+ORDER\s+BY\s+([\s\S]+?))?(?:\s+LIMIT\s+(\d+))?(?:\s+OFFSET\s+(\d+)(?:\s+ROWS?)?)?(?:\s+FETCH\s+(?:FIRST|NEXT)\s+(\d+)\s+ROWS?\s+ONLY)?\s*$/i.exec(statement)
  if (!match) throw preview()
  const [, top, list, written, where, groupBy, having, order, limit, offset, fetch] = match
  const resolved = resolveTable(tenant, source, tables, written!, after(statement, /\bFROM\s+/i))
  const { structure } = resolved
  const rows = rowsOf(tenant, source, resolved.tables, structure).filter(whereTest(where, structure, params, after(statement, /\bWHERE\s+/i)))
  const columnNamed = (name: string, at: number) => {
    const column = structure.columns.find(item => item.name.toLowerCase() === unquote(name.split('.').pop()!).toLowerCase())
    if (!column) throw sqlProblem(`column "${unquote(name.split('.').pop()!)}" does not exist`, at)
    return column
  }

  // The select list: columns and aggregates (COUNT(*), COUNT(DISTINCT c), SUM, AVG, MIN, MAX), with aliases
  interface Item { name: string; key: string; type: string | null; column?: string; agg?: { fn: string; column: string | null; distinct: boolean } }
  const items: Item[] = list!.trim() === '*'
    ? structure.columns.map(column => ({ name: column.name, key: column.name.toLowerCase(), type: column.type, column: column.name }))
    : splitOutside(list!, /^,/).map(item => {
        // `expr [AS] alias`, where expr is a column or ends with ")"
        const alias = /^([\s\S]+?)\s+(?:AS\s+)?"?([A-Za-z_]\w*)"?$/i.exec(item.trim())
        const hasAlias = !!alias && (/\)$/.test(alias[1]!.trim()) || /^[\w."]+$/.test(alias[1]!.trim()))
        const body = hasAlias ? alias![1]!.trim() : item.trim()
        const aliasName = hasAlias ? alias![2]! : null
        const agg = /^(COUNT|SUM|AVG|MIN|MAX)\s*\(\s*(DISTINCT\s+)?(\*|[\w."]+)\s*\)$/i.exec(body)
        if (agg) {
          const fn = agg[1]!.toLowerCase()
          const column = agg[3] === '*' ? null : columnNamed(agg[3]!, 7).name
          const type = fn === 'count' ? 'BIGINT' : fn === 'avg' ? 'NUMERIC' : column ? (structure.columns.find(c => c.name === column)?.type ?? null) : null
          return { name: aliasName ?? fn, key: body.toLowerCase().replace(/\s+/g, ''), type, agg: { fn, column, distinct: !!agg[2] } }
        }
        const column = columnNamed(body, 7)
        return { name: aliasName ?? column.name, key: column.name.toLowerCase(), type: column.type, column: column.name }
      })
  const grouped = !!groupBy || items.some(item => item.agg)
  const aggregate = (fn: string, values: unknown[]) => {
    const present = values.filter(value => value != null)
    if (fn === 'count') return present.length
    if (!present.length) return null
    const numbers = present.map(Number).filter(value => Number.isFinite(value))
    if (fn === 'sum') return Math.round(numbers.reduce((sum, value) => sum + value, 0) * 100) / 100
    if (fn === 'avg') return Math.round((numbers.reduce((sum, value) => sum + value, 0) / numbers.length) * 100) / 100
    const sorted = [...present].sort((x, y) => (typeof x === 'number' && typeof y === 'number' ? x - y : String(x).localeCompare(String(y), undefined, { numeric: true })))
    return fn === 'min' ? sorted[0] : sorted[sorted.length - 1]
  }
  let output: unknown[][]
  if (grouped) {
    const keys = groupBy ? splitOutside(groupBy, /^,/).map(name => columnNamed(name, after(statement, /\bGROUP\s+BY\s+/i)).name) : []
    const groups = new Map<string, TableRow[]>()
    for (const row of rows) {
      const key = JSON.stringify(keys.map(name => row[name] ?? null))
      groups.set(key, [...(groups.get(key) ?? []), row])
    }
    if (!keys.length && !groups.size) groups.set('[]', [])
    output = [...groups.values()].map(group =>
      items.map(item => {
        if (!item.agg) {
          if (keys.length && !keys.includes(item.column!)) throw sqlProblem(`column "${item.column}" must appear in the GROUP BY clause or be used in an aggregate function`, 7)
          return group[0]?.[item.column!] ?? null
        }
        const values = item.agg.column ? group.map(row => row[item.agg!.column!]) : group.map(() => 1)
        return aggregate(item.agg.fn, item.agg.distinct ? [...new Set(values.map(value => JSON.stringify(value)))].map(value => JSON.parse(value) as unknown) : values)
      }),
    )
  } else output = rows.map(row => items.map(item => row[item.column!] ?? null))

  // HAVING / ORDER BY name a column of the result: an alias, a column or an aggregate as written
  const indexOf = (expr: string, at: number) => {
    const text = expr.trim().toLowerCase().replace(/\s+/g, '')
    const found = items.findIndex(item => item.name.toLowerCase() === unquote(text) || item.key === text || item.key === unquote(text.split('.').pop()!))
    if (found < 0) throw sqlProblem(`column "${expr.trim()}" does not exist`, at)
    return found
  }
  if (having) {
    const at = after(statement, /\bHAVING\s+/i)
    const condition = /^([\s\S]+?)\s*(>=|<=|<>|!=|=|>|<)\s*(-?\d+(?:\.\d+)?)$/.exec(having.trim())
    if (!condition) throw preview()
    const index = indexOf(condition[1]!, at)
    const [op, limitValue] = [condition[2]!, Number(condition[3])]
    output = output.filter(row => {
      const value = Number(row[index])
      return op === '>' ? value > limitValue : op === '<' ? value < limitValue : op === '>=' ? value >= limitValue : op === '<=' ? value <= limitValue : op === '=' ? value === limitValue : value !== limitValue
    })
  }
  if (order) {
    const at = after(statement, /\bORDER\s+BY\s+/i)
    const keys = splitOutside(order, /^,/).map(part => {
      const [, expr, direction] = /^([\s\S]+?)(?:\s+(ASC|DESC))?$/i.exec(part.trim())!
      return { index: indexOf(expr!, at), desc: /DESC/i.test(direction ?? '') }
    })
    output = [...output].sort((a, b) => {
      for (const key of keys) {
        const x = a[key.index]
        const y = b[key.index]
        if (x == null && y == null) continue
        if (x == null) return 1
        if (y == null) return -1
        const result = typeof x === 'number' && typeof y === 'number' ? x - y : String(x).localeCompare(String(y), undefined, { numeric: true })
        if (result) return key.desc ? -result : result
      }
      return 0
    })
  }
  output = output.slice(Number(offset ?? 0))
  const cut = Number(top ?? limit ?? fetch ?? 0)
  if (cut) output = output.slice(0, cut)
  return { columns: items.map(item => ({ name: item.name, type: item.type })), rows: output }
}

/** The rows a changing statement will touch (for the confirm), and how to apply it. */
export interface PlannedChange {
  resolved: Resolved
  estimate: number
  apply: () => number
}

export function planChange(tenant: MockTenant, source: StoredDataSource, tables: DatabaseTable[], sql: string, params: Record<string, string>): PlannedChange {
  const statement = sql.trim()
  const update = /^UPDATE\s+([\w."`[\]]+)\s+SET\s+([\s\S]+?)(?:\s+WHERE\s+([\s\S]+))?$/i.exec(statement)
  const remove = /^DELETE\s+FROM\s+([\w."`[\]]+)(?:\s+WHERE\s+([\s\S]+))?$/i.exec(statement)
  const insert = /^INSERT\s+INTO\s+([\w."`[\]]+)\s*\(([^)]*)\)\s*VALUES\s*([\s\S]+)$/i.exec(statement)
  const written = (update ?? remove ?? insert)?.[1]
  if (!written) throw preview()
  const resolved = resolveTable(tenant, source, tables, written, statement.search(/\s/) + 1)
  const { structure } = resolved
  const rows = () => rowsOf(tenant, source, resolved.tables, structure)
  const changes = changesOf(source, structure)
  const typed = (assignments: [string, Value][]) => {
    const out: Record<string, unknown> = {}
    for (const [name, value] of assignments) {
      const column = structure.columns.find(item => item.name.toLowerCase() === unquote(name).toLowerCase())
      if (!column) throw sqlProblem(`column "${unquote(name)}" does not exist`, 0)
      const parsed = parseValue(column, value)
      if ('problem' in parsed) throw sqlProblem(`invalid value for column "${column.name}"`, 0)
      out[column.name] = parsed.value
    }
    return out
  }
  if (update) {
    const values = typed(splitOutside(update[2]!, /^,/).map(item => {
      const [name, ...rest] = item.split('=')
      return [name!.trim(), valueOf(rest.join('='), params, 0)] as [string, Value]
    }))
    if (Object.keys(values).some(name => structure.primary_key.includes(name))) throw sqlProblem('changing a key column is not supported here', 0)
    const test = whereTest(update[3], structure, params, after(statement, /\bWHERE\s+/i))
    const matching = rows().filter(test)
    return {
      resolved,
      estimate: matching.length,
      apply: () => {
        for (const row of matching) {
          const inserted = changes.inserted.find(item => item.__key === row.__key)
          if (inserted) Object.assign(inserted, values)
          else changes.updated[row.__key] = { ...changes.updated[row.__key], ...values }
        }
        return matching.length
      },
    }
  }
  if (remove) {
    const matching = rows().filter(whereTest(remove[2], structure, params, after(statement, /\bWHERE\s+/i)))
    return {
      resolved,
      estimate: matching.length,
      apply: () => {
        const keys = new Set(matching.map(row => row.__key))
        changes.inserted = changes.inserted.filter(row => !keys.has(row.__key))
        changes.deleted.push(...keys)
        return matching.length
      },
    }
  }
  const names = splitOutside(insert![2]!, /^,/)
  const tuples = splitOutside(insert![3]!, /^,/).map(tuple => splitOutside(tuple.replace(/^\(|\)$/g, ''), /^,/).map(value => valueOf(value, params, 0)))
  if (tuples.some(tuple => tuple.length !== names.length)) throw sqlProblem('INSERT has more expressions than target columns', 0)
  return {
    resolved,
    estimate: tuples.length,
    apply: () => {
      const existing = rows()
      for (const tuple of tuples) {
        const values = typed(names.map((name, index) => [name, tuple[index]!] as [string, Value]))
        for (const name of structure.primary_key) {
          const column = structure.columns.find(item => item.name === name)!
          if (values[name] == null && column.has_default) values[name] = existing.reduce((max, row) => Math.max(max, Number(row[name]) || 0), 0) + 1 + changes.inserted.length
        }
        const key = structure.primary_key.map(name => String(values[name] ?? '')).join('|')
        if (existing.some(row => row.__key === key)) throw sqlProblem('duplicate key value violates unique constraint', 0)
        changes.inserted.push({ ...values, __key: key } as TableRow)
      }
      return tuples.length
    },
  }
}

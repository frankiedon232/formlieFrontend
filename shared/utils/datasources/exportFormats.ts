/**
 * Table exports beyond CSV and Excel (F12 M3, owner 2026-10-05):
 * - JSON: an array with one object per row, keyed by column name; JSON columns keep their
 *   structure, numbers and yes / no stay typed, NULL stays null.
 * - SQL: INSERT statements written for the connection's own engine, to copy rows into another
 *   database or keep a copy. Names quoted the engine's way, text escaped, dates as the engine
 *   reads them, one statement per row (works on every version), inside one transaction.
 */
import type { DbEngine } from '#shared/utils/integrations/databases'
import { kindOfType } from '#shared/utils/datasources/values'
import { quoteName } from '#shared/utils/datasources/tables'

/** The most rows one explorer export takes (owner 2026-10-05): this page by default, "All rows" up to this many. */
export const EXPORT_MAX_ROWS = 5000

interface ExportColumn {
  name: string
  type: string
  primary?: boolean
  has_default?: boolean
}
type Row = Record<string, unknown>

const parsedJson = (value: unknown) => {
  if (typeof value !== 'string') return value
  try {
    return JSON.parse(value) as unknown
  } catch {
    return value
  }
}

/** One object per row, pretty-printed. */
export function jsonExport(columns: ExportColumn[], rows: Row[]): string {
  const list = rows.map(row =>
    Object.fromEntries(
      columns.map(column => {
        const value = row[column.name] ?? null
        return [column.name, value !== null && kindOfType(column.type) === 'json' ? parsedJson(value) : value]
      }),
    ),
  )
  return `${JSON.stringify(list, null, 2)}\n`
}

const stringLiteral = (engine: DbEngine, text: string) => {
  // MySQL and MariaDB treat backslash as an escape character by default.
  const escaped = (engine === 'mysql' || engine === 'mariadb' ? text.replace(/\\/g, '\\\\') : text).replace(/'/g, "''")
  return `${engine === 'sqlserver' ? 'N' : ''}'${escaped}'`
}

/** '2026-08-01T16:22:23.030Z' → '2026-08-01 16:22:23.030' (what every engine reads). */
const plainDateTime = (text: string) => text.replace('T', ' ').replace(/Z$|[+-]\d{2}:\d{2}$/, '')

/** A value written as an SQL literal for the column's type on this engine. */
export function sqlLiteral(engine: DbEngine, type: string, value: unknown): string {
  if (value === null || value === undefined) return 'NULL'
  switch (kindOfType(type)) {
    case 'integer':
    case 'decimal': {
      const number = Number(value)
      return Number.isFinite(number) ? String(number) : 'NULL'
    }
    case 'boolean': {
      const yes = value === true || value === 1 || value === '1' || String(value).toLowerCase() === 'true'
      return engine === 'postgresql' ? (yes ? 'TRUE' : 'FALSE') : yes ? '1' : '0'
    }
    case 'date': {
      const text = String(value).slice(0, 10)
      return engine === 'oracle' ? `DATE '${text}'` : `'${text}'`
    }
    case 'datetime': {
      const text = plainDateTime(String(value))
      return engine === 'oracle' ? `TIMESTAMP '${text}'` : `'${text}'`
    }
    case 'json':
      return stringLiteral(engine, typeof value === 'string' ? value : JSON.stringify(value))
    default:
      return stringLiteral(engine, typeof value === 'object' ? JSON.stringify(value) : String(value))
  }
}

/** The INSERT script for the rows, with a short header. */
export function sqlInsertScript(
  engine: DbEngine,
  target: { schema: string; table: string },
  columns: ExportColumn[],
  rows: Row[],
  madeAt = new Date(),
): string {
  const table = `${quoteName(engine, target.schema)}.${quoteName(engine, target.table)}`
  const names = columns.map(column => quoteName(engine, column.name)).join(', ')
  // SQL Server refuses values for an identity (auto-numbered) column unless switched on.
  const identity = engine === 'sqlserver' && columns.some(column => column.primary && column.has_default && kindOfType(column.type) === 'integer')
  const begin = { postgresql: 'BEGIN;', mysql: 'START TRANSACTION;', mariadb: 'START TRANSACTION;', sqlserver: 'BEGIN TRANSACTION;', oracle: null }[engine]
  const lines = [
    `-- ${target.schema}.${target.table}: ${rows.length} row(s)`,
    `-- Exported from Formalie on ${madeAt.toISOString()}`,
    '',
    ...(begin ? [begin] : []),
    ...(identity ? [`SET IDENTITY_INSERT ${table} ON;`] : []),
    ...rows.map(row => `INSERT INTO ${table} (${names}) VALUES (${columns.map(column => sqlLiteral(engine, column.type, row[column.name])).join(', ')});`),
    ...(identity ? [`SET IDENTITY_INSERT ${table} OFF;`] : []),
    'COMMIT;',
  ]
  return `${lines.join('\n')}\n`
}

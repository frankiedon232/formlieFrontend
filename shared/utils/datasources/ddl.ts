/**
 * Changing the structure of the organisation's own tables from the explorer (F12 M3, owner
 * 2026-10-05): create a table, add / change / delete a column, add / delete an index, rename,
 * empty (TRUNCATE) or delete a table. Never response tables (Formalie manages those) and only
 * with Full access. The browser shows exactly these statements before anything runs; the server
 * runs the same ones. Written per engine: quoting, types, identity columns, renames (sp_rename on
 * SQL Server), MODIFY (MySQL, MariaDB, Oracle), named default constraints on SQL Server.
 */
import type { DbEngine } from '#shared/utils/integrations/databases'
import { TABLE_PREFIXES } from '#shared/types/datasources'
import { quoteName, tableRestMax } from '#shared/utils/datasources/tables'
import { sqlLiteral } from '#shared/utils/datasources/exportFormats'
import { kindOfType, lengthOf } from '#shared/utils/datasources/values'

export const COLUMN_KINDS = ['text', 'long_text', 'integer', 'big_integer', 'decimal', 'boolean', 'date', 'datetime', 'time', 'json'] as const
export type ColumnKind = (typeof COLUMN_KINDS)[number]

/** A column as the forms describe it; the engine's type comes from `typeFor`. */
export interface ColumnSpec {
  name: string
  kind: ColumnKind
  /** Text length, or the digits of a decimal. */
  length?: number | null
  /** Digits after the decimal point. */
  scale?: number | null
  nullable: boolean
  /** As typed (empty = no default). */
  default?: string | null
  primary?: boolean
  /** Numbered automatically (whole-number primary keys). */
  auto?: boolean
}

export type TableChange =
  | { op: 'add_column'; column: ColumnSpec }
  | { op: 'alter_column'; column: string; to: ColumnSpec }
  | { op: 'drop_column'; column: string }
  | { op: 'rename_table'; name: string }
  | { op: 'add_index'; name: string; columns: string[]; unique: boolean }
  | { op: 'drop_index'; name: string }
  | { op: 'truncate' }
  | { op: 'drop_table' }

/** The column as it is now (for alter_column). */
export interface CurrentColumn {
  name: string
  type: string
  nullable: boolean
  /** Its default as typed (null = none). */
  default: string | null
  primary: boolean
}

export const TEXT_LENGTH_DEFAULT = 255
export const DECIMAL_DEFAULT = { length: 12, scale: 2 }

/** Kinds each engine offers (Oracle has no time-of-day type). */
export const kindsFor = (engine: DbEngine): ColumnKind[] => COLUMN_KINDS.filter(kind => !(engine === 'oracle' && kind === 'time'))

/** The engine's type for a column. */
export function typeFor(engine: DbEngine, spec: Pick<ColumnSpec, 'kind' | 'length' | 'scale'>): string {
  const length = spec.length || TEXT_LENGTH_DEFAULT
  const digits = spec.length || DECIMAL_DEFAULT.length
  const scale = spec.scale ?? DECIMAL_DEFAULT.scale
  const mysql = engine === 'mysql' || engine === 'mariadb'
  switch (spec.kind) {
    case 'text':
      return engine === 'sqlserver' ? `NVARCHAR(${length})` : engine === 'oracle' ? `VARCHAR2(${length})` : `VARCHAR(${length})`
    case 'long_text':
      return engine === 'sqlserver' ? 'NVARCHAR(MAX)' : engine === 'oracle' ? 'CLOB' : 'TEXT'
    case 'integer':
      return engine === 'oracle' ? 'NUMBER(10)' : engine === 'postgresql' ? 'INTEGER' : 'INT'
    case 'big_integer':
      return engine === 'oracle' ? 'NUMBER(19)' : 'BIGINT'
    case 'decimal':
      return engine === 'oracle' ? `NUMBER(${digits},${scale})` : engine === 'postgresql' ? `NUMERIC(${digits},${scale})` : `DECIMAL(${digits},${scale})`
    case 'boolean':
      return engine === 'postgresql' ? 'BOOLEAN' : mysql ? 'TINYINT(1)' : engine === 'sqlserver' ? 'BIT' : 'NUMBER(1)'
    case 'date':
      return 'DATE'
    case 'datetime':
      return engine === 'postgresql' ? 'TIMESTAMPTZ' : mysql ? 'DATETIME' : engine === 'sqlserver' ? 'DATETIME2' : 'TIMESTAMP'
    case 'time':
      return 'TIME'
    case 'json':
      return engine === 'postgresql' ? 'JSONB' : mysql ? 'JSON' : engine === 'sqlserver' ? 'NVARCHAR(MAX)' : 'CLOB'
  }
}

/** The kind and sizes of an existing column's type (for the edit form). */
export function specOfType(type: string): Pick<ColumnSpec, 'kind' | 'length' | 'scale'> {
  const t = type.toUpperCase()
  const kind = kindOfType(type)
  if (kind === 'integer') return { kind: /BIGINT|NUMBER\(19\)/.test(t) ? 'big_integer' : 'integer' }
  if (kind === 'decimal') {
    const match = /\((\d+)\s*,\s*(\d+)\)/.exec(t)
    return { kind: 'decimal', length: match ? Number(match[1]) : null, scale: match ? Number(match[2]) : null }
  }
  if (kind === 'text') {
    const length = lengthOf(type)
    return length ? { kind: 'text', length } : { kind: 'long_text' }
  }
  return { kind }
}

export type NameProblem = 'required' | 'chars' | 'long' | 'prefix'

/** A table, column or index name: a letter first, then letters, numbers and underscores. */
export function checkName(engine: DbEngine, name: string, what: 'table' | 'column' | 'index'): NameProblem | null {
  if (!name) return 'required'
  if (!/^[A-Za-z][A-Za-z0-9_]*$/.test(name)) return 'chars'
  if (name.length > tableRestMax(engine, '')) return 'long'
  if (what === 'table' && TABLE_PREFIXES.some(prefix => name.toLowerCase().startsWith(prefix))) return 'prefix'
  return null
}

/** Spaces become underscores; lower case (Oracle: upper case), like Formalie's own names. */
export const normaliseDbName = (engine: DbEngine, text: string) => {
  const joined = text.trim().replace(/\s+/g, '_')
  return engine === 'oracle' ? joined.toUpperCase() : joined.toLowerCase()
}

const tableRef = (engine: DbEngine, schema: string, table: string) => `${quoteName(engine, schema)}.${quoteName(engine, table)}`
const defaultName = (table: string, column: string) => `DF_${table}_${column}`
const literalOf = (engine: DbEngine, spec: ColumnSpec) => sqlLiteral(engine, typeFor(engine, spec), spec.default)

/** One column's definition inside CREATE TABLE / ADD. */
export function columnSql(engine: DbEngine, table: string, spec: ColumnSpec): string {
  const parts = [quoteName(engine, spec.name), typeFor(engine, spec)]
  const auto = spec.auto && spec.primary && (spec.kind === 'integer' || spec.kind === 'big_integer')
  if (auto) parts.push({ postgresql: 'GENERATED BY DEFAULT AS IDENTITY', oracle: 'GENERATED BY DEFAULT AS IDENTITY', sqlserver: 'IDENTITY(1,1)', mysql: '', mariadb: '' }[engine])
  if (!auto && spec.default) parts.push(engine === 'sqlserver' ? `CONSTRAINT ${quoteName(engine, defaultName(table, spec.name))} DEFAULT ${literalOf(engine, spec)}` : `DEFAULT ${literalOf(engine, spec)}`)
  if (!spec.nullable || spec.primary) parts.push('NOT NULL')
  if (auto && (engine === 'mysql' || engine === 'mariadb')) parts.push('AUTO_INCREMENT')
  return parts.filter(Boolean).join(' ')
}

/** CREATE TABLE with its columns and primary key. */
export function createTableStatements(engine: DbEngine, schema: string, table: string, columns: ColumnSpec[]): string[] {
  const primary = columns.filter(column => column.primary)
  const lines = [
    ...columns.map(column => `  ${columnSql(engine, table, column)}`),
    ...(primary.length ? [`  CONSTRAINT ${quoteName(engine, `${table}_pk`)} PRIMARY KEY (${primary.map(column => quoteName(engine, column.name)).join(', ')})`] : []),
  ]
  return [`CREATE TABLE ${tableRef(engine, schema, table)} (\n${lines.join(',\n')}\n);`]
}

/** The statements one change runs, in order. */
export function changeStatements(engine: DbEngine, schema: string, table: string, change: TableChange, current?: CurrentColumn): string[] {
  const ref = tableRef(engine, schema, table)
  const q = (name: string) => quoteName(engine, name)
  const mysql = engine === 'mysql' || engine === 'mariadb'
  switch (change.op) {
    case 'add_column':
      return [engine === 'oracle' ? `ALTER TABLE ${ref} ADD (${columnSql(engine, table, change.column)});` : engine === 'sqlserver' ? `ALTER TABLE ${ref} ADD ${columnSql(engine, table, change.column)};` : `ALTER TABLE ${ref} ADD COLUMN ${columnSql(engine, table, change.column)};`]
    case 'drop_column':
      return [`ALTER TABLE ${ref} DROP COLUMN ${q(change.column)};`]
    case 'rename_table':
      if (engine === 'sqlserver') return [`EXEC sp_rename N'${schema}.${table}', N'${change.name}';`]
      if (mysql) return [`RENAME TABLE ${ref} TO ${tableRef(engine, schema, change.name)};`]
      return [`ALTER TABLE ${ref} RENAME TO ${q(change.name)};`]
    case 'add_index':
      return [`CREATE ${change.unique ? 'UNIQUE ' : ''}INDEX ${q(change.name)} ON ${ref} (${change.columns.map(q).join(', ')});`]
    case 'drop_index':
      return [mysql || engine === 'sqlserver' ? `DROP INDEX ${q(change.name)} ON ${ref};` : `DROP INDEX ${q(schema)}.${q(change.name)};`]
    case 'truncate':
      return [`TRUNCATE TABLE ${ref};`]
    case 'drop_table':
      return [`DROP TABLE ${ref};`]
    case 'alter_column':
      return alterColumn(engine, schema, table, change.column, change.to, current)
  }
}

function alterColumn(engine: DbEngine, schema: string, table: string, name: string, to: ColumnSpec, current?: CurrentColumn): string[] {
  const ref = tableRef(engine, schema, table)
  const q = (value: string) => quoteName(engine, value)
  const out: string[] = []
  if (to.name !== name)
    out.push(engine === 'sqlserver' ? `EXEC sp_rename N'${schema}.${table}.${name}', N'${to.name}', N'COLUMN';` : `ALTER TABLE ${ref} RENAME COLUMN ${q(name)} TO ${q(to.name)};`)
  const column = q(to.name)
  const type = typeFor(engine, to)
  const typeChanged = !current || current.type.replace(/\s/g, '').toUpperCase() !== type.toUpperCase()
  const nullChanged = !current || current.nullable !== to.nullable
  const newDefault = to.default ? literalOf(engine, to) : null
  const defaultChanged = !current || (current.default ?? '') !== (to.default ?? '')
  if (!typeChanged && !nullChanged && !defaultChanged) return out
  switch (engine) {
    case 'postgresql':
      if (typeChanged) out.push(`ALTER TABLE ${ref} ALTER COLUMN ${column} TYPE ${type} USING ${column}::${type};`)
      if (nullChanged) out.push(`ALTER TABLE ${ref} ALTER COLUMN ${column} ${to.nullable ? 'DROP' : 'SET'} NOT NULL;`)
      if (defaultChanged) out.push(newDefault ? `ALTER TABLE ${ref} ALTER COLUMN ${column} SET DEFAULT ${newDefault};` : `ALTER TABLE ${ref} ALTER COLUMN ${column} DROP DEFAULT;`)
      break
    case 'mysql':
    case 'mariadb':
      out.push(`ALTER TABLE ${ref} MODIFY COLUMN ${column} ${type}${newDefault ? ` DEFAULT ${newDefault}` : ''}${to.nullable ? ' NULL' : ' NOT NULL'};`)
      break
    case 'sqlserver':
      if (typeChanged || nullChanged) out.push(`ALTER TABLE ${ref} ALTER COLUMN ${column} ${type}${to.nullable ? ' NULL' : ' NOT NULL'};`)
      if (defaultChanged) {
        const constraint = q(defaultName(table, to.name))
        out.push(`ALTER TABLE ${ref} DROP CONSTRAINT IF EXISTS ${constraint};`)
        if (newDefault) out.push(`ALTER TABLE ${ref} ADD CONSTRAINT ${constraint} DEFAULT ${newDefault} FOR ${column};`)
      }
      break
    case 'oracle':
      out.push(`ALTER TABLE ${ref} MODIFY (${column}${typeChanged ? ` ${type}` : ''}${defaultChanged ? ` DEFAULT ${newDefault ?? 'NULL'}` : ''}${nullChanged ? (to.nullable ? ' NULL' : ' NOT NULL') : ''});`)
      break
  }
  return out
}

/** Whether a type change may lose or refuse data (shown as a caution). */
export function typeChangeRisky(from: string, to: Pick<ColumnSpec, 'kind' | 'length' | 'scale'>): boolean {
  const before = specOfType(from)
  if (before.kind === to.kind) {
    if (to.kind === 'text') return (to.length ?? TEXT_LENGTH_DEFAULT) < (before.length ?? 0)
    if (to.kind === 'decimal') return (to.length ?? 0) < (before.length ?? 0) || (to.scale ?? 0) < (before.scale ?? 0)
    return false
  }
  const widening: Partial<Record<ColumnKind, ColumnKind[]>> = { integer: ['big_integer', 'decimal', 'text', 'long_text'], big_integer: ['decimal', 'text', 'long_text'], text: ['long_text'], decimal: ['text', 'long_text'], date: ['datetime', 'text', 'long_text'], boolean: ['integer', 'big_integer', 'text'] }
  return !(widening[before.kind] ?? []).includes(to.kind)
}

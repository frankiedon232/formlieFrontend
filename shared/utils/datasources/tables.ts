/**
 * Response tables (F12 M2, decision 113): turning a form into a table on a connection, matching a
 * form to an existing table, checking the match, and writing a response as a row. Used by the
 * storage editor (preview), the mock (and the real backend) when creating tables and delivering.
 *
 *   names    prefix + form name, lower snake case (Oracle upper case); columns from field keys;
 *            reserved words get a suffix; within each engine's length limit
 *   types    per field type and engine (text, numbers, dates, yes / no, JSON for answers with
 *            several values, links for files)
 *   rows     ISO dates, numbers as numbers, choices by value or label, several values as JSON or
 *            "; "-joined text, files as their secure links
 */
import type { ChoiceValue, DestinationColumn, DestinationSettings, MetaColumn, MultiValue, TableColumn } from '#shared/types/destinations'
import type { DbEngine } from '#shared/utils/integrations/databases'
import type { FormField } from '#shared/utils/forms/build'
import { answerText } from '#shared/utils/forms/answer-text'

const MAX_NAME: Record<DbEngine, number> = { postgresql: 63, mysql: 64, mariadb: 64, sqlserver: 128, oracle: 128 }

/** Words every engine (or one of them) refuses as a bare name. */
const RESERVED = new Set([
  'all', 'and', 'as', 'asc', 'between', 'by', 'case', 'check', 'column', 'comment', 'create', 'date', 'default', 'delete', 'desc', 'distinct', 'drop', 'else', 'end', 'exists', 'file', 'for',
  'from', 'grant', 'group', 'having', 'in', 'index', 'insert', 'into', 'is', 'join', 'key', 'level', 'like', 'limit', 'number', 'not', 'null', 'of', 'on', 'option', 'or', 'order', 'primary',
  'references', 'rows', 'select', 'session', 'size', 'table', 'then', 'to', 'trigger', 'uid', 'union', 'unique', 'update', 'user', 'values', 'view', 'when', 'where', 'with',
])

/** lower_snake_case, ASCII only (other letters dropped), never empty, never starting with a digit. */
export function snake(text: string): string {
  const out = text
    .normalize('NFKD')
    .replace(/[̀-ͯ]/g, '')
    .replace(/([a-z0-9])([A-Z])/g, '$1_$2')
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '_')
    .replace(/^_+|_+$/g, '')
  return /^[0-9]/.test(out) ? `c_${out}` : out
}

const cased = (engine: DbEngine, name: string) => (engine === 'oracle' ? name.toUpperCase() : name)

/** The table Formalie creates for a form: prefix + form name. */
export function tableNameFor(engine: DbEngine, prefix: string, formName: string): string {
  const base = snake(formName) || 'form'
  return cased(engine, `${prefix}${base}`.slice(0, MAX_NAME[engine]).replace(/_+$/, ''))
}

/** A column name for a field key, unique within `taken`. */
export function columnNameFor(engine: DbEngine, key: string, taken: Set<string>): string {
  let base = snake(key) || 'answer'
  if (RESERVED.has(base)) base = `${base}_value`
  base = base.slice(0, MAX_NAME[engine] - 3)
  let name = base
  for (let n = 2; taken.has(name.toLowerCase()); n++) name = `${base}_${n}`
  taken.add(name.toLowerCase())
  return cased(engine, name)
}

/** What may follow the prefix in a table Formalie creates (owner 2026-10-05). */
export const TABLE_REST_MIN = 6
export type TableNameProblem = 'required' | 'short' | 'chars' | 'long'

/** The part a person types after the prefix: more than 5 characters, letters, numbers and underscores only. */
export function checkTableRest(engine: DbEngine, prefix: string, rest: string): TableNameProblem | null {
  if (!rest) return 'required'
  if (!/^[A-Za-z0-9_]+$/.test(rest)) return 'chars'
  if (rest.length < TABLE_REST_MIN) return 'short'
  if (prefix.length + rest.length > MAX_NAME[engine]) return 'long'
  return null
}

/** The most characters that may follow the prefix on this engine. */
export const tableRestMax = (engine: DbEngine, prefix: string) => MAX_NAME[engine] - prefix.length

/** Spaces become underscores; lower case (Oracle: upper case), as Formalie names its tables. */
export const normaliseTableRest = (engine: DbEngine, text: string) => {
  const joined = text.replace(/\s+/g, '_')
  return engine === 'oracle' ? joined.toUpperCase() : joined.toLowerCase()
}

// ── Types ────────────────────────────────────────────────────────────────────────────────

type Kind = 'short' | 'long' | 'code' | 'decimal' | 'integer' | 'date' | 'time' | 'datetime' | 'boolean' | 'json' | 'links' | 'uuid'

const TYPES: Record<DbEngine, Record<Kind, string>> = {
  postgresql: { short: 'VARCHAR(1000)', long: 'TEXT', code: 'VARCHAR(320)', decimal: 'NUMERIC(18,4)', integer: 'INTEGER', date: 'DATE', time: 'TIME', datetime: 'TIMESTAMPTZ', boolean: 'BOOLEAN', json: 'JSONB', links: 'JSONB', uuid: 'UUID' },
  mysql: { short: 'VARCHAR(1000)', long: 'LONGTEXT', code: 'VARCHAR(320)', decimal: 'DECIMAL(18,4)', integer: 'INT', date: 'DATE', time: 'TIME', datetime: 'DATETIME(3)', boolean: 'TINYINT(1)', json: 'JSON', links: 'JSON', uuid: 'CHAR(36)' },
  mariadb: { short: 'VARCHAR(1000)', long: 'LONGTEXT', code: 'VARCHAR(320)', decimal: 'DECIMAL(18,4)', integer: 'INT', date: 'DATE', time: 'TIME', datetime: 'DATETIME(3)', boolean: 'TINYINT(1)', json: 'LONGTEXT', links: 'LONGTEXT', uuid: 'CHAR(36)' },
  sqlserver: { short: 'NVARCHAR(1000)', long: 'NVARCHAR(MAX)', code: 'NVARCHAR(320)', decimal: 'DECIMAL(18,4)', integer: 'INT', date: 'DATE', time: 'TIME', datetime: 'DATETIMEOFFSET', boolean: 'BIT', json: 'NVARCHAR(MAX)', links: 'NVARCHAR(MAX)', uuid: 'UNIQUEIDENTIFIER' },
  oracle: { short: 'VARCHAR2(1000 CHAR)', long: 'CLOB', code: 'VARCHAR2(320 CHAR)', decimal: 'NUMBER(18,4)', integer: 'NUMBER(10)', date: 'DATE', time: 'VARCHAR2(8)', datetime: 'TIMESTAMP WITH TIME ZONE', boolean: 'NUMBER(1)', json: 'CLOB', links: 'CLOB', uuid: 'VARCHAR2(36)' },
}

const SEVERAL = new Set(['checkbox', 'multi_select', 'ranking', 'matrix', 'date_range', 'duration', 'full_name', 'address'])
const FILES = new Set(['file_upload', 'image_upload', 'signature'])

function kindOfField(type: string, multi: MultiValue): Kind {
  if (SEVERAL.has(type)) return multi === 'json' ? 'json' : 'long'
  if (FILES.has(type)) return multi === 'json' ? 'links' : 'long'
  switch (type) {
    case 'long_text':
    case 'rich_text':
      return 'long'
    case 'email':
    case 'phone':
    case 'url':
    case 'domain':
    case 'ip_address':
    case 'mac_address':
    case 'iban':
    case 'bic':
    case 'color':
    case 'country':
    case 'language':
    case 'timezone':
    case 'currency_code':
      return 'code'
    case 'number':
    case 'currency':
    case 'percentage':
    case 'slider':
    case 'calculated':
      return 'decimal'
    case 'rating':
    case 'scale':
      return 'integer'
    case 'date':
      return 'date'
    case 'time':
      return 'time'
    case 'datetime':
      return 'datetime'
    case 'toggle':
    case 'consent':
      return 'boolean'
    default:
      return 'short'
  }
}

const META_KIND: Record<MetaColumn, Kind> = { response_id: 'uuid', submitted_at: 'datetime', form_version: 'integer', language: 'code', response_number: 'integer', respondent_email: 'code', review_status: 'code' }

export const columnTypeFor = (engine: DbEngine, field: Pick<FormField, 'type'>, multi: MultiValue) => TYPES[engine][kindOfField(field.type, multi)]
export const metaTypeFor = (engine: DbEngine, meta: MetaColumn) => TYPES[engine][META_KIND[meta]]

/** The columns of a new table for a form: the response facts first, then a column per answer. */
export function columnsForForm(engine: DbEngine, fields: Pick<FormField, 'key' | 'type'>[], settings: Pick<DestinationSettings, 'multi_value'>, meta: MetaColumn[] = ['response_id', 'submitted_at', 'form_version', 'language']): DestinationColumn[] {
  const taken = new Set<string>()
  const metaColumns = meta.map(key => ({ column: columnNameFor(engine, key, taken), type: metaTypeFor(engine, key), source: { kind: 'meta' as const, key }, nullable: key !== 'response_id' && key !== 'submitted_at', existing: false }))
  const fieldColumns = fields.map(field => ({ column: columnNameFor(engine, field.key, taken), type: columnTypeFor(engine, field, settings.multi_value), source: { kind: 'field' as const, key: field.key }, nullable: true, existing: false }))
  return [...metaColumns, ...fieldColumns]
}

// ── SQL ──────────────────────────────────────────────────────────────────────────────────

export function quoteName(engine: DbEngine, name: string): string {
  if (engine === 'mysql' || engine === 'mariadb') return `\`${name.replace(/`/g, '``')}\``
  if (engine === 'sqlserver') return `[${name.replace(/]/g, ']]')}]`
  return `"${name.replace(/"/g, '""')}"`
}
const qualified = (engine: DbEngine, schema: string, table: string) => (schema ? `${quoteName(engine, schema)}.${quoteName(engine, table)}` : quoteName(engine, table))

/** CREATE TABLE for a response table; the response id is the primary key. */
export function createTableSql(engine: DbEngine, schema: string, table: string, columns: DestinationColumn[]): string {
  const key = columns.find(column => column.source?.kind === 'meta' && column.source.key === 'response_id')
  const lines = columns.map(column => `  ${quoteName(engine, column.column)} ${column.type}${column.nullable ? '' : ' NOT NULL'}`)
  if (key) lines.push(`  CONSTRAINT ${quoteName(engine, `${table}_pk`.slice(0, MAX_NAME[engine]))} PRIMARY KEY (${quoteName(engine, key.column)})`)
  return `CREATE TABLE ${qualified(engine, schema, table)} (\n${lines.join(',\n')}\n);`
}

/** ALTER TABLE … ADD for a field added to the form later (never drops anything). */
export function addColumnSql(engine: DbEngine, schema: string, table: string, column: Pick<DestinationColumn, 'column' | 'type'>): string {
  const add = engine === 'sqlserver' || engine === 'oracle' ? 'ADD' : 'ADD COLUMN'
  const body = engine === 'oracle' ? `(${quoteName(engine, column.column)} ${column.type})` : `${quoteName(engine, column.column)} ${column.type}`
  return `ALTER TABLE ${qualified(engine, schema, table)} ${add} ${body};`
}

/** A unique key for update-or-insert on a column of an existing table. */
export function uniqueKeySql(engine: DbEngine, schema: string, table: string, column: string): string {
  return `CREATE UNIQUE INDEX ${quoteName(engine, `${table}_${column}_uq`.slice(0, MAX_NAME[engine]))} ON ${qualified(engine, schema, table)} (${quoteName(engine, column)});`
}

/**
 * Formalie's standard for the tables it creates (owner 2026-10-05, not a choice): one row per
 * response, found by its response id. A new response adds the row, an edit or a review change
 * updates it, and a retried delivery can never add a duplicate.
 */
export function standardSettings<T extends Pick<DestinationSettings, 'write_mode' | 'key_column'>>(settings: T, columns: DestinationColumn[]): T {
  const id = columns.find(column => column.source?.kind === 'meta' && column.source.key === 'response_id')
  return { ...settings, write_mode: 'upsert', key_column: id?.column ?? settings.key_column }
}

/**
 * A view over a response table with each column named after its question, for the organisation's
 * own systems and reports (they run it in their database; Formalie never does).
 */
export function viewSql(engine: DbEngine, schema: string, table: string, columns: DestinationColumn[], labels: Map<string, string>): string {
  const view = `${table}_view`.slice(0, MAX_NAME[engine])
  const used = new Set<string>()
  const lines = columns.map(column => {
    const key = column.source?.kind === 'field' ? column.source.key : null
    let alias = (key && labels.get(key)?.trim()) || column.column
    alias = alias.replace(/["`[\]]/g, '').slice(0, MAX_NAME[engine])
    for (let n = 2; used.has(alias.toLowerCase()); n++) alias = `${alias.slice(0, MAX_NAME[engine] - 3)} ${n}`
    used.add(alias.toLowerCase())
    return `  ${quoteName(engine, column.column)} AS ${quoteName(engine, alias)}`
  })
  const create = engine === 'sqlserver' ? 'CREATE OR ALTER VIEW' : 'CREATE OR REPLACE VIEW'
  return `${create} ${qualified(engine, schema, view)} AS\nSELECT\n${lines.join(',\n')}\nFROM ${qualified(engine, schema, table)};`
}

// ── Matching an existing table ───────────────────────────────────────────────────────────

const norm = (name: string) => snake(name).replace(/_/g, '')
const META_ALIASES: Record<MetaColumn, string[]> = {
  response_id: ['responseid', 'formalieid', 'submissionid'],
  submitted_at: ['submittedat', 'createdat', 'receivedat', 'submissiondate'],
  form_version: ['formversion', 'version'],
  language: ['language', 'lang', 'locale'],
  response_number: ['responsenumber', 'number', 'reference'],
  respondent_email: ['respondentemail', 'email'],
  review_status: ['reviewstatus', 'status'],
}

/** Map an existing table's columns to the form: same name (ignoring case and underscores) first. */
export function matchColumns(columns: TableColumn[], fields: Pick<FormField, 'key' | 'label' | 'type'>[]): DestinationColumn[] {
  const used = new Set<string>()
  const pick = (candidates: string[]) => {
    for (const candidate of candidates) {
      const hit = columns.find(column => !used.has(column.name) && norm(column.name) === candidate)
      if (hit) {
        used.add(hit.name)
        return hit
      }
    }
    return null
  }
  const sources = new Map<string, DestinationColumn['source']>()
  for (const key of ['response_id', 'submitted_at', 'form_version', 'language', 'response_number', 'review_status'] as MetaColumn[]) {
    const hit = pick(META_ALIASES[key])
    if (hit) sources.set(hit.name, { kind: 'meta', key })
  }
  for (const field of fields) {
    const hit = pick([norm(field.key), norm(field.label ?? '')].filter(Boolean))
    if (hit) sources.set(hit.name, { kind: 'field', key: field.key })
  }
  return columns.map(column => ({ column: column.name, type: column.type, source: sources.get(column.name) ?? null, nullable: column.nullable || column.has_default, existing: true }))
}

// ── Checks ───────────────────────────────────────────────────────────────────────────────

export type MappingIssue =
  | { code: 'no_key'; column: null }
  | { code: 'required_unmapped'; column: string }
  | { code: 'type_mismatch'; column: string; field: string }
  | { code: 'duplicate_source'; column: string }
  | { code: 'upsert_key'; column: string }

const family = (type: string): 'text' | 'number' | 'date' | 'bool' | 'json' | 'other' => {
  const t = type.toUpperCase()
  if (/BOOL|^BIT$|TINYINT\(1\)|NUMBER\(1\)/.test(t)) return 'bool'
  if (/JSON/.test(t)) return 'json'
  if (/INT|NUM|DEC|FLOAT|DOUBLE|REAL|MONEY/.test(t)) return 'number'
  if (/DATE|TIME/.test(t)) return 'date'
  if (/CHAR|TEXT|CLOB|STRING|UNIQUEIDENTIFIER|UUID/.test(t)) return 'text'
  return 'other'
}
const fieldFamily = (type: string, multi: MultiValue) => family(TYPES.postgresql[kindOfField(type, multi)])

/** What stops (or weakens) a mapping. Text columns accept anything; JSON also takes text. */
export function checkMapping(columns: DestinationColumn[], fields: Pick<FormField, 'key' | 'type'>[], settings: DestinationSettings): MappingIssue[] {
  const issues: MappingIssue[] = []
  if (!columns.some(column => column.source?.kind === 'meta' && column.source.key === 'response_id')) issues.push({ code: 'no_key', column: null })
  const seen = new Set<string>()
  for (const column of columns) {
    if (!column.source && !column.nullable) issues.push({ code: 'required_unmapped', column: column.column })
    if (!column.source) continue
    const id = `${column.source.kind}:${column.source.key}`
    if (seen.has(id)) issues.push({ code: 'duplicate_source', column: column.column })
    seen.add(id)
    if (column.source.kind !== 'field') continue
    const field = fields.find(item => item.key === (column.source as { key: string }).key)
    if (!field) continue
    const want = fieldFamily(field.type, settings.multi_value)
    const have = family(column.type)
    if (have !== 'text' && have !== 'other' && have !== want && !(have === 'json' && want === 'text')) issues.push({ code: 'type_mismatch', column: column.column, field: field.key })
  }
  if (settings.write_mode === 'upsert' && !columns.some(column => column.column === settings.key_column && column.source)) issues.push({ code: 'upsert_key', column: settings.key_column })
  return issues
}

/** Issues that block saving (the rest are warnings). */
export const blocking = (issues: MappingIssue[]) => issues.filter(issue => issue.code !== 'type_mismatch')

// ── Rows ─────────────────────────────────────────────────────────────────────────────────

export interface ResponseFacts {
  id: string
  submitted_at: string
  form_version: number | null
  language: string
  number: number
  email: string | null
  review_status: string
}

/** A response as the row Formalie writes (values as the driver receives them). */
export function rowFor(columns: DestinationColumn[], fields: FormField[], answers: Record<string, unknown>, facts: ResponseFacts, settings: Pick<DestinationSettings, 'multi_value' | 'choices'>, fileLink: (value: unknown) => string[] = () => []): Record<string, unknown> {
  const row: Record<string, unknown> = {}
  const byKey = new Map(fields.map(field => [field.key, field]))
  const meta: Record<MetaColumn, unknown> = { response_id: facts.id, submitted_at: facts.submitted_at, form_version: facts.form_version, language: facts.language, response_number: facts.number, respondent_email: facts.email, review_status: facts.review_status }
  for (const column of columns) {
    if (!column.source) continue
    if (column.source.kind === 'meta') row[column.column] = meta[column.source.key] ?? null
    else row[column.column] = valueFor(byKey.get(column.source.key), answers[column.source.key], settings.multi_value, settings.choices, fileLink)
  }
  return row
}

function valueFor(field: FormField | undefined, value: unknown, multi: MultiValue, choices: ChoiceValue, fileLink: (value: unknown) => string[]): unknown {
  if (value == null || value === '' || (Array.isArray(value) && !value.length)) return null
  if (!field) return typeof value === 'object' ? JSON.stringify(value) : value
  const label = (v: unknown) => (choices === 'label' ? (field.options?.find(option => option.value === String(v))?.label ?? String(v)) : String(v))
  if (FILES.has(field.type)) {
    const links = fileLink(value)
    return multi === 'json' ? JSON.stringify(links) : links.join('; ')
  }
  if (SEVERAL.has(field.type)) {
    if (multi === 'text') return choices === 'label' || !Array.isArray(value) ? answerText(field, value) : value.map(String).join('; ')
    const shaped = Array.isArray(value) ? value.map(label) : field.type === 'matrix' && typeof value === 'object' ? Object.fromEntries(Object.entries(value as Record<string, unknown>).map(([row, v]) => [row, label(v)])) : value
    return JSON.stringify(shaped)
  }
  switch (kindOfField(field.type, multi)) {
    case 'decimal':
    case 'integer': {
      const number = Number(value)
      return Number.isFinite(number) ? number : null
    }
    case 'boolean':
      return value === true || value === 'true' || value === 'yes'
    case 'long':
      return String(value)
    default:
      return field.options?.length ? label(value) : typeof value === 'object' ? JSON.stringify(value) : String(value)
  }
}

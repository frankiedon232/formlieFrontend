/**
 * Rows and structure of the tables a connection shows in the mock explorer (F12 M3). Response
 * tables hold exactly the rows Formalie wrote (every delivered response, through `rowFor`); the
 * organisation's tables get believable rows made from the column names (neutral international
 * names, example.com addresses, reserved phone numbers), the same on every read.
 */
import type { DatabaseTable } from '#shared/types/destinations'
import type { ExplorerColumn, ForeignKey, ReadOnlyReason, TableIndex, TableRow, TableStructure } from '#shared/types/explorer'
import { createTableSql, quoteName, rowFor } from '#shared/utils/datasources/tables'
import { sqlLiteral } from '#shared/utils/datasources/exportFormats'
import { seedOf } from './dataSourceSim'
import type { StoredDataSource } from './dataSourceStore'
import { deliveriesOf, destinationsOf, inputFieldsOf, type StoredDestination } from './destinationStore'
import { formsOf } from './formStore'
import { answersOf, formResponses } from './responseData'
import type { MockTenant } from './tenants'
import { changesOf, structureEditOf } from './tableEdits'

const FIRST = ['Amara', 'Liam', 'Mei', 'Arjun', 'Selin', 'Kwame', 'Elena', 'Yuki', 'Mateo', 'Priya', 'Noah', 'Ingrid', 'Malik', 'Sara', 'Kenji', 'Leila', 'Omar', 'Chloe', 'Tomas', 'Aisha']
const LAST = ['Okafor', 'Kowalski', 'Chen', 'Sharma', 'Haddad', 'Mensah', 'Rossi', 'Tanaka', 'Silva', 'Ito', 'Laurent', 'Lindqvist', 'Rahman', 'Costa', 'Nguyen', 'Kaya', 'Santos', 'Adeyemi', 'Petrova', 'Hughes']
const COMPANIES = ['Northwind Labs', 'Bluefield Partners', 'Orbit Logistics', 'Cedar & Co', 'Lumen Health', 'Harbour Foods', 'Atlas Engineering', 'Kestrel Media']
const COUNTRIES = ['Brazil', 'Canada', 'Germany', 'India', 'Japan', 'Kenya', 'Mexico', 'Nigeria', 'Poland', 'Singapore', 'Turkey', 'United Kingdom']
const STATUSES = ['open', 'pending', 'in_progress', 'closed']
const TITLES = ['Contract review', 'Employment question', 'Lease renewal', 'Supplier dispute', 'Data request', 'Insurance claim', 'Visa application', 'Planning permission']
const MESSAGES = ['Could someone call me back this week?', 'Please send the price list for next quarter.', 'We would like a demo for our team.', 'Is delivery possible to our second office?', 'Following up on my earlier message.', 'Can we move the meeting to Thursday?']
const DEPARTMENTS = ['Finance', 'Operations', 'People', 'Sales', 'Support', 'Technology']
const DAY = 86_400_000

const pick = <T>(list: T[], n: number) => list[n % list.length]!
const ymd = (time: number) => new Date(time).toISOString().slice(0, 10)
const uuidish = (n: number) => {
  const hex = (seedOf(`row${n}`).toString(16) + seedOf(`r${n}x`).toString(16) + seedOf(`r${n}y`).toString(16) + seedOf(`r${n}z`).toString(16)).padEnd(32, '0').slice(0, 32)
  return `${hex.slice(0, 8)}-${hex.slice(8, 12)}-4${hex.slice(13, 16)}-a${hex.slice(17, 20)}-${hex.slice(20)}`
}

/** A believable value for a column of an organisation's table, from its name and type. */
function valueFor(column: ExplorerColumn, index: number, seed: number, counts: Map<string, number>, tableName: string): unknown {
  const name = column.name.toLowerCase()
  const s = seedOf(`${seed}:${name}:${index}`)
  const person = { first: pick(FIRST, seedOf(`${seed}f${index}`)), last: pick(LAST, seedOf(`${seed}l${index}`)) }
  if (column.primary && /int|num|bigint/i.test(column.type)) return index + 1
  if (column.references) return 1 + (s % Math.max(1, counts.get(`${column.references.schema}.${column.references.table}`) ?? 20))
  if (!column.primary && column.nullable && s % 11 === 0) return null
  if (name.includes('submission_id')) return uuidish(seed + index)
  const thing = /campaign|supplier|department/i.test(tableName)
  if (name === 'full_name' || (name === 'name' && !thing)) return `${person.first} ${person.last}`
  if (name === 'first_name') return person.first
  if (name === 'last_name') return person.last
  if (name.includes('email')) return `${person.first}.${person.last}@example.com`.toLowerCase()
  if (name.includes('phone')) return `+44 7700 900${String(s % 1000).padStart(3, '0')}`
  if (name.includes('company')) return pick(COMPANIES, s)
  if (name.includes('country')) return pick(COUNTRIES, s)
  if (name === 'status') return pick(STATUSES, s)
  if (name === 'title') return pick(TITLES, s)
  if (name.includes('message')) return pick(MESSAGES, s)
  if (name.includes('cost_centre')) return `CC-${100 + (s % 40)}`
  if (name === 'name') return pick([...COMPANIES, ...DEPARTMENTS], s)
  if (/date|_on$|_at$/.test(name) || /DATE|TIME/i.test(column.type)) {
    const time = Date.now() - (s % 365) * DAY - (s % 86_000) * 1000
    return /TIME/i.test(column.type) && !/^DATE$/i.test(column.type) ? new Date(time).toISOString() : ymd(time)
  }
  if (/BOOL|BIT|TINYINT\(1\)|NUMBER\(1\)/i.test(column.type)) return s % 3 !== 0
  if (/DEC|NUMERIC|NUMBER\(12/i.test(column.type)) return Math.round(((s % 500000) + (s % 100) / 100) * 100) / 100
  if (/INT|NUMBER/i.test(column.type)) return s % 1000
  return `${column.name} ${index + 1}`
}

// ── Structure ────────────────────────────────────────────────────────────────────────────

const destinationFor = (tenant: MockTenant, source: StoredDataSource, table: DatabaseTable): StoredDestination | undefined =>
  destinationsOf(tenant).find(item => item.datasource_id === source.id && item.table.created && item.table.schema === table.schema && item.table.name === table.name)

/** Columns named <thing>_id point at the table <things> when it exists. */
function referencesOf(tables: DatabaseTable[], table: DatabaseTable, column: string): ExplorerColumn['references'] {
  const match = /^(.+)_id$/i.exec(column)
  if (!match || table.formalie) return null
  const base = match[1]!.toLowerCase()
  const target = tables.find(item => !item.formalie && [`${base}s`, `${base}es`, base.replace(/y$/, 'ies')].includes(item.name.toLowerCase()))
  if (!target) return null
  const key = target.columns.find(item => item.primary)
  return key ? { schema: target.schema, table: target.name, column: key.name } : null
}

/** The numbered-key clause of a column (MySQL and MariaDB put AUTO_INCREMENT last). */
const identityOf = (engine: StoredDataSource['engine'], column: ExplorerColumn) =>
  column.primary && column.has_default && /INT|NUMBER/i.test(column.type) ? ({ postgresql: ' GENERATED BY DEFAULT AS IDENTITY', oracle: ' GENERATED BY DEFAULT AS IDENTITY', sqlserver: ' IDENTITY(1,1)', mysql: '', mariadb: '' } as const)[engine] : ''

export function structureOf(tenant: MockTenant, source: StoredDataSource, tables: DatabaseTable[], table: DatabaseTable): TableStructure {
  const engine = source.engine
  const destination = destinationFor(tenant, source, table)
  const form = destination ? formsOf(tenant).forms.find(item => item.id === destination.form_id) : undefined
  const edit = table.formalie ? undefined : structureEditOf(source, table)
  const columns: ExplorerColumn[] = table.columns.map(column => ({ ...column, default: edit?.defaults[column.name] ?? (column.has_default && column.primary && /INT|NUMBER/i.test(column.type) ? (engine === 'postgresql' ? 'generated by default as identity' : 'auto increment') : null), references: referencesOf(tables, table, column.name) }))
  const primary = columns.filter(column => column.primary).map(column => column.name)
  const indexes: TableIndex[] = [
    ...(primary.length ? [{ name: `${table.name}_pk`, columns: primary, unique: true, primary: true }] : []),
    ...columns.filter(column => column.unique && !column.primary).map(column => ({ name: `${table.name}_${column.name}_uq`, columns: [column.name], unique: true, primary: false })),
    ...(destination ? destination.columns.filter(column => column.source?.kind === 'meta' && column.source.key === 'submitted_at').map(column => ({ name: `${table.name}_${column.column}_idx`, columns: [column.column], unique: false, primary: false })) : []),
    ...(edit?.indexes ?? []),
  ].filter(index => !edit?.droppedIndexes.includes(index.name))
  const foreign_keys: ForeignKey[] = columns
    .filter(column => column.references)
    .map(column => ({ name: `${table.name}_${column.name}_fk`, columns: [column.name], references: { schema: column.references!.schema, table: column.references!.table, columns: [column.references!.column] } }))
  const ddl = destination
    ? createTableSql(engine, table.schema, table.name, destination.columns)
    : [
        `CREATE TABLE ${quoteName(engine, table.schema)}.${quoteName(engine, table.name)} (`,
        [
          ...columns.map(column => `  ${quoteName(engine, column.name)} ${column.type}${identityOf(engine, column)}${edit?.defaults[column.name] ? ` DEFAULT ${sqlLiteral(engine, column.type, edit.defaults[column.name])}` : ''}${column.nullable ? '' : ' NOT NULL'}${column.primary && column.has_default && (engine === 'mysql' || engine === 'mariadb') ? ' AUTO_INCREMENT' : ''}`),
          ...(primary.length ? [`  CONSTRAINT ${quoteName(engine, `${table.name}_pk`)} PRIMARY KEY (${primary.map(name => quoteName(engine, name)).join(', ')})`] : []),
          ...foreign_keys.map(key => `  CONSTRAINT ${quoteName(engine, key.name)} FOREIGN KEY (${quoteName(engine, key.columns[0]!)}) REFERENCES ${quoteName(engine, key.references.schema)}.${quoteName(engine, key.references.table)} (${quoteName(engine, key.references.columns[0]!)})`),
        ].join(',\n'),
        ');',
      ].join('\n')
  const read_only: ReadOnlyReason = table.formalie ? 'response_table' : source.access.other !== 'read_write' ? 'read_access' : !primary.length ? 'no_key' : null
  // Structure changes: their own tables with Full access only, never response tables (owner 2026-10-05)
  const alterable = !table.formalie && source.access.other === 'read_write'
  return { schema: table.schema, name: table.name, kind: 'table', formalie: table.formalie, form: form ? { id: form.id, name: form.name } : null, columns, primary_key: primary, indexes, foreign_keys, rows_estimate: table.rows_estimate, ddl, read_only, alterable }
}

// ── Rows ─────────────────────────────────────────────────────────────────────────────────

export { changesOf, type TableChanges } from './tableEdits'

const keyOf = (row: Record<string, unknown>, primary: string[], index: number) => (primary.length ? primary.map(name => String(row[name] ?? '')).join('|') : `#${index + 1}`)

/** Every row of a table (as stored), oldest first. */
export function rowsOf(tenant: MockTenant, source: StoredDataSource, tables: DatabaseTable[], structure: TableStructure): TableRow[] {
  const table = tables.find(item => item.schema === structure.schema && item.name === structure.name)!
  const destination = destinationFor(tenant, source, table)
  if (destination) {
    const form = formsOf(tenant).forms.find(item => item.id === destination.form_id)
    if (!form) return []
    const sent = new Set(deliveriesOf(tenant, destination, form).filter(delivery => delivery.status === 'sent').map(delivery => delivery.response_id))
    const fields = inputFieldsOf(form)
    return formResponses(tenant, form)
      .filter(entry => sent.has(entry.id))
      .sort((a, b) => a.at - b.at)
      .map((entry, index) => {
        const row = rowFor(destination.columns, fields, answersOf(form, entry), { id: entry.id, submitted_at: new Date(entry.at).toISOString(), form_version: entry.form_version, language: entry.language, number: entry.number, email: entry.respondent.email ?? null, review_status: entry.status }, destination.settings, value =>
          (Array.isArray(value) ? value : []).map(file => `https://api.formalie.dev/files/${seedOf(`${entry.id}${(file as { name?: string })?.name ?? ''}`).toString(36)}`),
        )
        return { ...row, __key: keyOf(row, structure.primary_key, index) }
      })
  }
  // A table changed here keeps the generated values of where it came from; new columns start empty.
  const edit = structureEditOf(source, table)
  const origin = edit?.origin ?? `${table.schema}.${table.name}`
  const originName = origin.slice(origin.indexOf('.') + 1)
  const seed = seedOf(`${source.id}${origin.replace('.', '')}`)
  const counts = new Map(tables.map(item => [`${item.schema}.${item.name}`, item.rows_estimate ?? 20] as [string, number]))
  const total = edit?.created || edit?.truncated ? 0 : (table.rows_estimate ?? 0)
  const generated: TableRow[] = Array.from({ length: total }, (_, index) => {
    const row: Record<string, unknown> = {}
    for (const column of structure.columns) {
      const from = edit ? edit.columnOrigin[column.name] : column.name
      row[column.name] = from == null ? (edit?.defaults[column.name] ?? null) : valueFor({ ...column, name: from }, index, seed, counts, originName)
    }
    return { ...row, __key: keyOf(row, structure.primary_key, index) }
  })
  const edits = changesOf(source, table)
  const deleted = new Set(edits.deleted)
  return [...generated, ...edits.inserted].filter(row => !deleted.has(row.__key)).map(row => (edits.updated[row.__key] ? { ...row, ...edits.updated[row.__key] } : row))
}

/**
 * The tables a connection shows in the mock (F12 M2, reused by the explorer in M3). Nothing
 * connects to a real database: each connection gets a believable set of the organisation's own
 * tables (by engine; the seeded ones by their purpose) plus the response tables Formalie created
 * there. What Formalie may see follows the connection's access: with "None" only its own tables.
 */
import type { DatabaseTable, TableColumn } from '#shared/types/destinations'
import type { DbEngine } from '#shared/utils/integrations/databases'
import { tablesSchemaOf } from '#shared/utils/datasources/permissions'
import { seedOf } from './dataSourceSim'
import type { StoredDataSource } from './dataSourceStore'

type Spec = [name: string, kind: 'id' | 'text' | 'long' | 'email' | 'date' | 'datetime' | 'number' | 'money' | 'bool' | 'key', required?: boolean]

const T: Record<DbEngine, Record<Spec[1], string>> = {
  postgresql: { id: 'BIGINT', key: 'VARCHAR(64)', text: 'VARCHAR(200)', long: 'TEXT', email: 'VARCHAR(320)', date: 'DATE', datetime: 'TIMESTAMPTZ', number: 'INTEGER', money: 'NUMERIC(12,2)', bool: 'BOOLEAN' },
  mysql: { id: 'BIGINT', key: 'VARCHAR(64)', text: 'VARCHAR(200)', long: 'TEXT', email: 'VARCHAR(320)', date: 'DATE', datetime: 'DATETIME', number: 'INT', money: 'DECIMAL(12,2)', bool: 'TINYINT(1)' },
  mariadb: { id: 'BIGINT', key: 'VARCHAR(64)', text: 'VARCHAR(200)', long: 'TEXT', email: 'VARCHAR(320)', date: 'DATE', datetime: 'DATETIME', number: 'INT', money: 'DECIMAL(12,2)', bool: 'TINYINT(1)' },
  sqlserver: { id: 'BIGINT', key: 'NVARCHAR(64)', text: 'NVARCHAR(200)', long: 'NVARCHAR(MAX)', email: 'NVARCHAR(320)', date: 'DATE', datetime: 'DATETIME2', number: 'INT', money: 'DECIMAL(12,2)', bool: 'BIT' },
  oracle: { id: 'NUMBER(19)', key: 'VARCHAR2(64)', text: 'VARCHAR2(200)', long: 'CLOB', email: 'VARCHAR2(320)', date: 'DATE', datetime: 'TIMESTAMP', number: 'NUMBER(10)', money: 'NUMBER(12,2)', bool: 'NUMBER(1)' },
}

/** Tables by connection purpose (seeded) or a general set (anything added later). */
const SETS: Record<string, Record<string, Spec[]>> = {
  cases: {
    clients: [['id', 'id', true], ['full_name', 'text', true], ['email', 'email'], ['phone', 'text'], ['created_at', 'datetime', true]],
    cases: [['id', 'id', true], ['client_id', 'id', true], ['title', 'text', true], ['status', 'text', true], ['opened_at', 'date', true], ['closed_at', 'date']],
    referrals: [['submission_id', 'key', true], ['full_name', 'text'], ['email', 'email'], ['phone', 'text'], ['message', 'long'], ['submitted_at', 'datetime']],
  },
  leads: {
    leads: [['submission_id', 'key', true], ['name', 'text'], ['email', 'email'], ['phone', 'text'], ['company', 'text'], ['message', 'long'], ['created_at', 'datetime']],
    campaigns: [['id', 'id', true], ['name', 'text', true], ['budget', 'money'], ['starts_on', 'date']],
  },
  people: {
    employees: [['id', 'id', true], ['first_name', 'text', true], ['last_name', 'text', true], ['email', 'email'], ['department_id', 'number'], ['start_date', 'date']],
    departments: [['id', 'id', true], ['name', 'text', true], ['cost_centre', 'text']],
  },
  finance: {
    INVOICES: [['ID', 'id', true], ['SUPPLIER_ID', 'id', true], ['AMOUNT', 'money', true], ['DUE_ON', 'date'], ['PAID', 'bool']],
    SUPPLIERS: [['ID', 'id', true], ['NAME', 'text', true], ['COUNTRY', 'text'], ['EMAIL', 'email']],
  },
  general: {
    customers: [['id', 'id', true], ['full_name', 'text', true], ['email', 'email'], ['phone', 'text'], ['created_at', 'datetime']],
    orders: [['id', 'id', true], ['customer_id', 'id', true], ['total', 'money'], ['ordered_at', 'datetime']],
    contact_requests: [['submission_id', 'key', true], ['full_name', 'text'], ['email', 'email'], ['phone', 'text'], ['message', 'long'], ['received_at', 'datetime']],
  },
}

function purposeOf(source: StoredDataSource): string {
  const database = String(source.settings.database ?? source.settings.service_name ?? '').toLowerCase()
  if (database.includes('case')) return 'cases'
  if (database.includes('lead')) return 'leads'
  if (database.includes('people')) return 'people'
  if (database.includes('fin')) return 'finance'
  return 'general'
}

const columnsOf = (engine: DbEngine, specs: Spec[]): TableColumn[] =>
  specs.map(([name, kind, required], i) => ({ name, type: T[engine][kind], nullable: !required, has_default: kind === 'id' && i === 0, primary: i === 0 && (kind === 'id' || kind === 'key'), unique: i === 0 }))

/** Response tables Formalie created on a connection (filled in by the destination store). */
export interface CreatedTable {
  schema: string
  name: string
  columns: { column: string; type: string; nullable: boolean }[]
  rows: number
}

/** Every table Formalie may see on this connection: the organisation's (per access) and its own. */
export function tablesOf(source: StoredDataSource, created: CreatedTable[]): DatabaseTable[] {
  const engine = source.engine
  const own: DatabaseTable[] = created.map(table => ({
    schema: table.schema,
    name: table.name,
    columns: table.columns.map((column, i) => ({ name: column.column, type: column.type, nullable: column.nullable, has_default: false, primary: i === 0, unique: i === 0 })),
    rows_estimate: table.rows,
    formalie: true,
  }))
  if (source.access.other === 'none') return own
  const set = SETS[purposeOf(source)]!
  const schemas = source.access.schemas.length ? source.access.schemas : [engine === 'mysql' || engine === 'mariadb' ? String(source.settings.database) : engine === 'postgresql' ? 'public' : engine === 'sqlserver' ? 'dbo' : 'APP']
  const theirs: DatabaseTable[] = []
  Object.entries(set).forEach(([name, specs], i) => {
    const schema = schemas[i % schemas.length]!
    if (schema === tablesSchemaOf(engine, source.settings, source.access) && own.some(table => table.name === name)) return
    theirs.push({ schema, name, columns: columnsOf(engine, specs), rows_estimate: 40 + (seedOf(`${source.id}${name}`) % 900), formalie: false })
  })
  return [...own, ...theirs].sort((a, b) => Number(b.formalie) - Number(a.formalie) || a.schema.localeCompare(b.schema) || a.name.localeCompare(b.name))
}

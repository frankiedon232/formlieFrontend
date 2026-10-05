/**
 * Database explorer (F12 M3). What Formalie may see on a connection follows its access: with
 * "None" only the response tables, otherwise the schemas allowed. Response tables are read-only
 * here (they change through Formalie: edit the response instead); the organisation's tables can be
 * changed with Full access. Every export, change and import is recorded in the audit trail.
 */
import type { TableColumn } from './destinations'

export interface ExplorerColumn extends TableColumn {
  default: string | null
  /** Points at another table (foreign key). */
  references: { schema: string; table: string; column: string } | null
}

export interface TableIndex {
  name: string
  columns: string[]
  unique: boolean
  primary: boolean
}

export interface ForeignKey {
  name: string
  columns: string[]
  references: { schema: string; table: string; columns: string[] }
}

/** Why rows of a table can't be changed here (null = they can). */
export type ReadOnlyReason = 'response_table' | 'read_access' | 'no_key' | 'view' | null

export interface TableStructure {
  schema: string
  name: string
  kind: 'table' | 'view'
  /** A response table Formalie created (and for which form). */
  formalie: boolean
  form: { id: string; name: string } | null
  columns: ExplorerColumn[]
  primary_key: string[]
  indexes: TableIndex[]
  foreign_keys: ForeignKey[]
  rows_estimate: number | null
  /** The table's definition (read only). */
  ddl: string
  read_only: ReadOnlyReason
}

/** A row as stored; `__key` identifies it (its primary key) for the detail panel and changes. */
export type TableRow = Record<string, unknown> & { __key: string }

/** Distinct values of a low-variety column (the Filter menu). */
export interface ColumnFacet {
  column: string
  values: { value: string; count: number }[]
}

export interface TableExport {
  id: string
  table: string
  format: 'csv' | 'xlsx'
  status: 'running' | 'ready'
  progress: number
  rows: number
  size: number | null
}

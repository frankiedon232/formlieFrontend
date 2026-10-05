/**
 * Response storage (F12 M2, decision 113): a form's responses are kept in Formalie's encrypted
 * storage (the default) or in a table of one of the workspace's connections: a table Formalie
 * creates from the form (named with the connection's prefix), or an existing table of theirs
 * (Full access needed). Each response is delivered in the background, retried, and has a status.
 */
import type { DataSourceStatus, DbEngine } from './datasources'

/** Where a value in a row comes from: an answer, or a fact about the response. */
export const META_COLUMNS = ['response_id', 'submitted_at', 'form_version', 'language', 'response_number', 'respondent_email', 'review_status'] as const
export type MetaColumn = (typeof META_COLUMNS)[number]
/** Always written (the key and when). */
export const REQUIRED_META: MetaColumn[] = ['response_id', 'submitted_at']

export type ColumnSource = { kind: 'field'; key: string } | { kind: 'meta'; key: MetaColumn }

export interface DestinationColumn {
  column: string
  /** The database type (as the engine names it). */
  type: string
  source: ColumnSource | null
  nullable: boolean
  /** Part of the table before Formalie touched it (existing tables), or created by Formalie. */
  existing: boolean
}

export interface TableColumn {
  name: string
  type: string
  nullable: boolean
  has_default: boolean
  primary: boolean
  unique: boolean
}

export interface DatabaseTable {
  schema: string
  name: string
  columns: TableColumn[]
  rows_estimate: number | null
  /** Created by Formalie (name starts with the connection's prefix). */
  formalie: boolean
}

export type WriteMode = 'insert' | 'upsert'
/** How answers with several values (picks, ranking, matrix, name, address, files) are stored. */
export type MultiValue = 'json' | 'text'
/** Choices stored by their value (stable) or their label (readable). */
export type ChoiceValue = 'value' | 'label'

export interface DestinationSettings {
  write_mode: WriteMode
  /** Column an update-or-insert matches on (default response_id). */
  key_column: string
  multi_value: MultiValue
  choices: ChoiceValue
}

export type DestinationStatus = 'active' | 'paused' | 'failing'
export type DeliveryStatus = 'sent' | 'pending' | 'failed' | 'held' | 'not_sent'

export interface DestinationRow {
  id: string
  form: { id: string; name: string; status: string }
  datasource: { id: string; name: string; engine: DbEngine; status: DataSourceStatus }
  table: { schema: string; name: string; created: boolean }
  status: DestinationStatus
  settings: DestinationSettings
  sent_30d: number
  pending: number
  failed: number
  last_delivery_at: string | null
  daily: { date: string; count: number }[]
  /** Form fields without a column yet (offer "Add column"). */
  new_fields: number
  created_by: { id: string; name: string }
  created_at: string
  updated_at: string
}

export interface DestinationDetail extends DestinationRow {
  columns: DestinationColumn[]
  /** The form's answer fields (labels for the column list). */
  fields: { key: string; label: string }[]
  /** Fields added to the form since: key, label, the column it would get. */
  unmapped_fields: { key: string; label: string; column: string; type: string }[]
  backfill: BackfillJob | null
  /** Earliest response time the destination covers (created, or the oldest sent by a backfill). */
  covers_from: string
  /** How many of the form's responses were never sent (before it was set up). */
  not_sent: number
}

export interface Delivery {
  response_id: string
  number: number
  submitted_at: string
  respondent: string | null
  status: DeliveryStatus
  attempts: number
  error_code: string | null
  at: string | null
  next_retry_at: string | null
}

export interface BackfillJob {
  id: string
  from: string
  to: string
  total: number
  done: number
  status: 'running' | 'done'
  started_at: string
  finished_at: string | null
}

export interface DestinationInsights {
  total: number
  by_status: Record<DestinationStatus, number>
  sent_30d: number
  previous_30d: number
  daily: { date: string; count: number }[]
  deliveries: Record<'sent' | 'pending' | 'failed' | 'held', number>
}

/** The form's storage, for its overview card. */
export interface FormStorage {
  mode: 'formalie' | 'database'
  destination: DestinationRow | null
  /** Connections the person may choose (none yet: offer Add connection). */
  connections: number
}

/** A new or changed destination. */
export interface DestinationSaveRequest {
  form_id: string
  datasource_id: string
  table: { mode: 'create' | 'existing'; schema: string; name: string }
  columns: { column: string; type: string; source: ColumnSource | null; nullable: boolean; existing: boolean }[]
  settings: DestinationSettings
}

/** A form's answer field, as the storage setup needs it. */
export interface StorageField {
  key: string
  label: string
  type: string
  options?: { value: string; label: string }[]
}

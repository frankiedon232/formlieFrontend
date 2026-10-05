/**
 * Data sources (F12): the organisation's own databases. Connection settings are per engine
 * (shared/utils/datasources/engines.ts); secrets (passwords, keys, certificates) are write-only:
 * sent once in the encrypted envelope, kept encrypted on the server, never returned. The API only
 * says which secrets are set (`secrets_set`) and when they last changed.
 */
import type { DbEngine } from '#shared/utils/integrations/databases'

export type { DbEngine }

/** connected · attention (works, but something needs a look, e.g. a missing permission) · failing · disabled · untested */
export const DATASOURCE_STATUSES = ['connected', 'attention', 'failing', 'disabled', 'untested'] as const
export type DataSourceStatus = (typeof DATASOURCE_STATUSES)[number]

/** Prefixes for the tables Formalie creates (owner 2026-10-05). */
export const TABLE_PREFIXES = ['formalie_', 'fmly_', 'form_'] as const
export type TablePrefix = (typeof TABLE_PREFIXES)[number]
/** The organisation's other tables (optional): not shared · read · read and write. */
export type OtherTablesAccess = 'none' | 'read' | 'read_write'

/** Non-secret, engine-specific settings (host, port, database, TLS mode, …). */
export type DataSourceSettings = Record<string, string | number | boolean>
/** Secret values, only ever sent to the server (create, or change credentials). */
export type DataSourceSecrets = Record<string, string>

/**
 * A connection exists to store the workspace's responses (owner 2026-10-05, not negotiable):
 * Formalie always creates its own tables (one per form, named with the prefix), writes every
 * response there, reads them back to show them, changes and removes rows and adds columns, in its
 * own tables only. Access to the organisation's other tables is optional, for the explorer,
 * queries, option lists from their data and imports.
 */
export interface DataSourceAccessSettings {
  table_prefix: TablePrefix
  /** Schema for Formalie's tables (PostgreSQL, SQL Server); empty = the engine's default. */
  tables_schema: string
  other: OtherTablesAccess
  /** Schemas (MySQL / MariaDB: databases) with the other tables; empty = the connection's own. */
  schemas: string[]
}

export interface DataSourceConfig {
  engine: DbEngine
  settings: DataSourceSettings
  access: DataSourceAccessSettings
}

/** A row on Data sources → Connections. */
export interface DataSourceRow {
  id: string
  name: string
  engine: DbEngine
  /** host:port (or the Oracle descriptor's host), shown left to right */
  address: string
  database: string
  access: DataSourceAccessSettings
  status: DataSourceStatus
  enabled: boolean
  server_version: string | null
  latency_ms: number | null
  last_checked_at: string | null
  /** share of passed health checks in the last 30 days (0 to 100), null before the first check */
  uptime_30d: number | null
  /** Formalie operations in the last 30 days, day by day (reads, writes, checks) */
  operations_30d: number
  daily: { date: string; count: number }[]
  forms_count: number
  missing_permissions: number
  created_by: { id: string; name: string }
  created_at: string
  updated_at: string
}

export interface DataSourceCheck {
  at: string
  status: 'passed' | 'warning' | 'failed'
  latency_ms: number | null
  error_code: string | null
}

export interface DataSourceDetail extends DataSourceRow {
  settings: DataSourceSettings
  /** Which secret fields are set (values never leave the server). */
  secrets_set: string[]
  secrets_changed_at: string | null
  last_test: ConnectionTest | null
  /** Recent health checks, newest first. */
  checks: DataSourceCheck[]
  /** Daily uptime for the last 30 days (null = no checks that day). */
  uptime_daily: { date: string; uptime: number | null }[]
  forms: { id: string; name: string }[]
}

export interface DataSourceInsights {
  total: number
  by_status: Record<DataSourceStatus, number>
  forms_sending: number
  operations_30d: number
  previous_30d: number
  daily: { date: string; count: number }[]
  avg_latency_ms: number | null
  missing_permissions: number
}

export interface DataSourceMeta {
  /** Formalie's outgoing addresses, to allow in the database's firewall (platform setting). */
  egress_ips: string[]
}

// ── Connection test ──────────────────────────────────────────────────────────────────────

export const TEST_STEPS = ['network', 'ssh', 'tls', 'sign_in', 'database', 'permissions'] as const
export type TestStepKey = (typeof TEST_STEPS)[number]
export type TestStepStatus = 'pending' | 'running' | 'passed' | 'warning' | 'failed' | 'skipped'

export interface TestStep {
  key: TestStepKey
  status: TestStepStatus
  duration_ms: number | null
  /** FRM-DEST-* code when the step failed or warned */
  error_code: string | null
}

export type PermissionStatus = 'granted' | 'missing' | 'not_needed'

export interface PermissionResult {
  operation: string
  status: PermissionStatus
}

/** Something worth changing although the connection works (least privilege, encryption). */
export type TestFinding = 'tls_off' | 'trust_certificate' | 'missing_permissions'

export interface ConnectionTest {
  id: string
  status: 'running' | 'passed' | 'warning' | 'failed'
  started_at: string
  finished_at: string | null
  steps: TestStep[]
  server_version: string | null
  latency_ms: number | null
  permissions: PermissionResult[]
  findings: TestFinding[]
  schemas: string[]
  tables_count: number | null
}

/** POST /datasources/test: a new configuration, or a saved connection with changes. */
export interface ConnectionTestRequest extends DataSourceConfig {
  datasource_id?: string
  secrets?: DataSourceSecrets
}

export interface DataSourceSaveRequest extends DataSourceConfig {
  name: string
  secrets?: DataSourceSecrets
  /** The test run whose result becomes the connection's status. */
  test_id?: string
}

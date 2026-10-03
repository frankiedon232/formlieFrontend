/** Audit trail shapes (docs/API-CONTRACT.md → Audit trail). */
import type { AuditAction, AuditArea } from '../utils/audit/events'

export type AuditOutcome = 'success' | 'failure' | 'blocked'
export type AuditSeverity = 'info' | 'notice' | 'warning' | 'critical'

export interface AuditActor {
  type: 'user' | 'api_key' | 'system'
  /** null when nobody was signed in (e.g. a failed sign-in with an unknown email). */
  id: string | null
  name: string
  email: string | null
}

export interface AuditResource {
  /** form, user, session, workspace, setting, api_key, destination, webhook, export… */
  type: string
  id: string | null
  name: string | null
}

export interface AuditLocation {
  ip: string
  city: string | null
  /** ISO 3166-1 alpha-2, e.g. `GB`; null for private / unknown addresses. */
  country: string | null
}

export interface AuditDevice {
  type: 'desktop' | 'mobile' | 'tablet' | 'unknown'
  browser: string | null
  os: string | null
}

export interface AuditChange {
  field: string
  before: string | number | boolean | null
  after: string | number | boolean | null
}

export interface AuditEvent {
  id: string
  occurred_at: string
  action: AuditAction
  area: AuditArea
  outcome: AuditOutcome
  severity: AuditSeverity
  actor: AuditActor
  resource: AuditResource | null
  organisation: { id: string; name: string } | null
  location: AuditLocation
  device: AuditDevice
  /** Before / after values for changes; empty for actions without changed fields. */
  changes: AuditChange[]
  /** Extra facts, e.g. `{ method: 'password', channel: 'email' }`. */
  metadata: Record<string, string>
  /** FRM-* code when the action failed or was blocked. */
  reason: string | null
  request_id: string
}

/** GET /audit-logs/facets — options for the person and country filters. */
export interface AuditFacets {
  actors: { id: string; name: string }[]
  countries: string[]
}

export type ExportFormat = 'xlsx' | 'csv'

/** POST /audit-logs/export → a background job; poll GET /exports/{id}. */
export interface ExportJob {
  id: string
  status: 'queued' | 'running' | 'done' | 'failed'
  /** 0–100 */
  progress: number
  rows: number
  format: ExportFormat
  file_name: string
  /** One-time, short-lived download link once `status` is `done`. */
  download_url: string | null
  expires_at: string | null
}

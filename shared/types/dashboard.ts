/**
 * Dashboard (F21, design reference 2: docs/design/Screenshot 2026-10-02 092034.png). One page with views:
 * Workspace (the home: every area at a glance and what needs attention), Forms, Data sources, API service.
 * Every number respects the person's role and folder access (docs/API-CONTRACT.md → Dashboard).
 */
export const DASHBOARD_VIEWS = ['workspace', 'forms', 'data', 'api'] as const
export type DashboardView = (typeof DASHBOARD_VIEWS)[number]
export const DASHBOARD_GROUPS = ['day', 'week', 'month', 'year'] as const
export type DashboardGroup = (typeof DASHBOARD_GROUPS)[number]

/** A number with the same number for the period before (null = not comparable). */
export interface DashboardKpi {
  value: number
  previous: number | null
}

/** One bucket of the activity chart (a day, a week, a month or a year, by its first day). */
export interface DashboardPoint {
  start: string
  /** Responses sent, and people who started (sent or not). */
  responses: number
  starts: number
  /** Calls to the API service (people who can see it). */
  api_calls: number
}

export type AttentionKind = 'to_review' | 'form_closing' | 'form_full' | 'connection_failing' | 'connection_attention' | 'webhook_failing' | 'plan_forms' | 'payment_due' | 'card_expiring'

/** Something to look at, most urgent first. */
export interface AttentionItem {
  kind: AttentionKind
  /** What it is about (a form, a connection, a webhook), when there is one. */
  name: string | null
  count: number | null
  at: string | null
  link: string
}

export type TimelineKind = 'opens' | 'closes' | 'renews' | 'plan_change' | 'card_expires'

/** What is coming up (the design's work timeline). */
export interface TimelineItem {
  kind: TimelineKind
  name: string | null
  at: string
  link: string
}

export interface DashboardTopForm {
  id: string
  name: string
  status: string
  responses: number
  previous: number
  completion_rate: number
  to_review: number
  /** Responses per bucket, for a small line. */
  trend: number[]
}

/** GET /dashboard?from&to&group */
export interface WorkspaceDashboard {
  from: string
  to: string
  group: DashboardGroup
  kpis: {
    responses: DashboardKpi
    completion_rate: DashboardKpi
    active_forms: DashboardKpi
    to_review: DashboardKpi
    attention: DashboardKpi
  }
  series: DashboardPoint[]
  top_forms: DashboardTopForm[]
  attention: AttentionItem[]
  timeline: TimelineItem[]
  /** Each area at a glance (null when the person's role doesn't reach it). */
  areas: {
    forms: { total: number; published: number; drafts: number; closed: number }
    data: { connections: number; connected: number; failing: number } | null
    api: { calls: number; previous: number; errors: number; services: number } | null
    plan: { plan: string; forms: number; forms_limit: number | null; ai_used: number; ai_limit: number | null } | null
  }
}

export type FormsWorkKind = 'stale_draft' | 'no_responses' | 'unpublished_changes' | 'closing' | 'nearly_full'

/** GET /dashboard/forms?from&to&group (F21 M2): running the forms. */
export interface FormsDashboard {
  from: string
  to: string
  group: DashboardGroup
  kpis: {
    published: DashboardKpi
    created: DashboardKpi
    per_form: DashboardKpi
    silent: DashboardKpi
    unpublished: DashboardKpi
  }
  by_status: { draft: number; published: number; closed: number; archived: number }
  /** Forms made per bucket. */
  created: { start: string; count: number }[]
  channels: { link: number; embed: number; api: number }
  top: { id: string; name: string; status: string; responses: number; previous: number; completion_rate: number }[]
  folders: { id: string | null; name: string | null; forms: number; responses: number }[]
  owners: { id: string; name: string; forms: number; responses: number }[]
  work: { kind: FormsWorkKind; form: { id: string; name: string }; at: string | null; count: number | null }[]
}

/** GET /dashboard/data?from&to&group (F21 M3): the data sources at work (people with data access). */
export interface DataDashboard {
  from: string
  to: string
  group: DashboardGroup
  kpis: {
    connections: DashboardKpi
    operations: DashboardKpi
    deliveries: DashboardKpi
    failing: DashboardKpi
    /** Average time to answer the last health checks, in milliseconds. */
    latency: DashboardKpi
  }
  /** Operations on the connections and responses stored in databases, per bucket. */
  series: { start: string; operations: number; deliveries: number }[]
  connections: { id: string; name: string; engine: string; status: string; latency_ms: number | null; last_checked_at: string | null; operations: number }[]
  /** What people did (the audit trail's data area), by kind. */
  kinds: { queries: number; rows: number; structure: number; exports: number; storage: number; connections: number }
  storage: { forms: number; sent: number; pending: number; failed: number }
  recent: { id: string; action: string; actor: string; resource: string | null; at: string }[]
}

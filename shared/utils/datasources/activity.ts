/**
 * Data sources → Activity (F12 M5): what happened on the organisation's connections, from the
 * audit trail (area `data`), grouped into kinds people think in. Used by the page's filter and
 * chart, and by the mock's insights.
 */
import type { AuditAction } from '#shared/utils/audit/events'

export const ACTIVITY_KINDS = ['queries', 'rows', 'structure', 'exports', 'storage', 'connections'] as const
export type ActivityKind = (typeof ACTIVITY_KINDS)[number]

export const ACTIVITY_ACTIONS: Record<ActivityKind, AuditAction[]> = {
  queries: ['data.query_run', 'data.saved_query_saved', 'data.saved_query_deleted'],
  rows: ['data.row_inserted', 'data.row_updated', 'data.row_deleted'],
  structure: ['data.user_table_created', 'data.table_altered', 'data.table_truncated', 'data.table_dropped'],
  exports: ['data.table_exported', 'data.query_exported'],
  storage: ['data.destination_created', 'data.destination_updated', 'data.destination_paused', 'data.destination_resumed', 'data.destination_removed', 'data.table_created', 'data.column_added', 'data.backfill_started', 'data.deliveries_retried'],
  connections: ['data.connection_created', 'data.connection_updated', 'data.connection_tested', 'data.connection_duplicated', 'data.connection_enabled', 'data.connection_disabled', 'data.connection_deleted', 'data.credentials_changed'],
}

/** The kind an action belongs to (null for actions outside Data sources). */
export const kindOfAction = (action: string): ActivityKind | null => ACTIVITY_KINDS.find(kind => (ACTIVITY_ACTIONS[kind] as string[]).includes(action)) ?? null

/** The kind colours: monochrome ink and the theme's status colours (rule 21). */
export const ACTIVITY_COLOR: Record<ActivityKind, string> = {
  queries: 'bg-(--ui-text-highlighted)',
  rows: 'bg-amber-500',
  structure: 'bg-violet-500',
  exports: 'bg-green-500',
  storage: 'bg-(--ui-text-dimmed)',
  connections: 'bg-(--ui-border-accented)',
}

/** The chart cards' numbers (`GET /datasources/activity/insights`). */
export interface ActivityInsights {
  total_30d: number
  previous_30d: number
  failed_30d: number
  daily: { date: string; count: number }[]
  by_kind: Record<ActivityKind, number>
  by_connection: { id: string; name: string; count: number }[]
}

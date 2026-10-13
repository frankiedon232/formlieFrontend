/**
 * DEVELOPMENT ONLY. The audit trail's filters in the mock (API-CONTRACT.md → Audit trail), shared by the list and the
 * export: kept apart from the route so tests can run them.
 */
import type { AuditEvent } from '#shared/types/audit'
import { auditPeriodFrom } from '#shared/utils/audit/period'

export type Query = Record<string, unknown>

const list = (query: Query, key: string) => {
  const value = query[`filter[${key}]`]
  return typeof value === 'string' && value ? value.split(',') : null
}
const day = (value: unknown, end: boolean) =>
  typeof value === 'string' && value ? Date.parse(`${value}T${end ? '23:59:59' : '00:00:00'}Z`) : null

/** Filters from API-CONTRACT.md → Audit trail (shared by the list and the export). Without a `from`, the last 90 days
 * (owner 2026-10-13, as the backend: query review Q8). */
export function filterEvents(events: AuditEvent[], query: Query): AuditEvent[] {
  const area = list(query, 'area')
  const action = list(query, 'action')
  const outcome = list(query, 'outcome')
  const actor = list(query, 'actor_id')
  const country = list(query, 'country')
  const resourceType = list(query, 'resource_type')
  const resourceId = list(query, 'resource_id')
  const from = day(auditPeriodFrom(typeof query.from === 'string' ? query.from : null), false)
  const to = day(query.to, true)
  return events.filter(event => {
    const at = Date.parse(event.occurred_at)
    return (
      (!area || area.includes(event.area)) &&
      (!action || action.includes(event.action)) &&
      (!outcome || outcome.includes(event.outcome)) &&
      (!actor || (event.actor.id !== null && actor.includes(event.actor.id))) &&
      (!country || country.includes(event.location.country ?? '')) &&
      (!resourceType || resourceType.includes(event.resource?.type ?? '')) &&
      (!resourceId || resourceId.includes(event.resource?.id ?? '')) &&
      (from === null || at >= from) &&
      (to === null || at <= to)
    )
  })
}

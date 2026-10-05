/**
 * Mock Data sources → Activity insights (F12 M5). The list itself is the audit trail
 * (`GET /audit-logs?filter[area]=data`); this adds the chart cards' numbers.
 *
 *   GET /datasources/activity/insights   last 30 days: total and the change, failed, per day, per kind, per connection
 */
import { ACTIVITY_KINDS, kindOfAction, type ActivityKind } from '#shared/utils/datasources/activity'
import { auditLogOf } from '../core/audit'
import { requireAdmin } from '../core/auth'
import { ok } from '../core/respond'
import { defineMockRoute } from '../core/route'

const DAY = 86_400_000

export const dataActivityInsights = defineMockRoute(({ event }) => {
  const { tenant } = requireAdmin(event)
  const now = Date.now()
  const data = auditLogOf(tenant).filter(item => item.area === 'data')
  const recent = data.filter(item => now - Date.parse(item.occurred_at) < 30 * DAY)
  const previous = data.filter(item => {
    const age = now - Date.parse(item.occurred_at)
    return age >= 30 * DAY && age < 60 * DAY
  })
  const daily = Array.from({ length: 30 }, (_, index) => {
    const date = new Date(now - (29 - index) * DAY).toISOString().slice(0, 10)
    return { date, count: recent.filter(item => item.occurred_at.slice(0, 10) === date).length }
  })
  const by_kind = Object.fromEntries(ACTIVITY_KINDS.map(kind => [kind, recent.filter(item => kindOfAction(item.action) === kind).length])) as Record<ActivityKind, number>
  const connections = new Map<string, { id: string; name: string; count: number }>()
  for (const item of recent) {
    const id = item.resource?.type === 'data_source' ? item.resource.id : null
    if (!id) continue
    const entry = connections.get(id) ?? { id, name: item.resource?.name ?? '', count: 0 }
    entry.count++
    connections.set(id, entry)
  }
  return ok({
    total_30d: recent.length,
    previous_30d: previous.length,
    failed_30d: recent.filter(item => item.outcome !== 'success').length,
    daily,
    by_kind,
    by_connection: [...connections.values()].sort((a, b) => b.count - a.count),
  })
})

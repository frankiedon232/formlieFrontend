/**
 * Dashboard, Data sources view (F21 M3, docs/API-CONTRACT.md → Dashboard): the connections at work. Needs
 * `data.view` (else FRM-PERM-1001).
 *
 *   GET /dashboard/data?from&to&group → DataDashboard
 */
import type { DataDashboard } from '#shared/types/dashboard'
import { bucketStart } from '#shared/utils/dashboard/buckets'
import { ACTIVITY_KINDS, kindOfAction } from '#shared/utils/datasources/activity'
import { auditLogOf } from '../core/audit'
import { requireAuth } from '../core/auth'
import { MockError, ok } from '../core/respond'
import { defineMockRoute } from '../core/route'
import { checksOf, dataSourcesOf, statusOf } from '../data/dataSourceStore'
import { deliveriesOf, destinationsOf } from '../data/destinationStore'
import { formsOf } from '../data/formStore'
import { permissionsOf } from '../data/rolesStore'
import { periodFrom } from './dashboard'

const iso = (time: number) => new Date(time).toISOString().slice(0, 10)

export const dataDashboard = defineMockRoute(({ event, query }) => {
  const { tenant, user } = requireAuth(event)
  if (!permissionsOf(user, tenant).has('data.view')) throw new MockError('FRM-PERM-1001')
  const { from, to, group, prevFrom, end, buckets } = periodFrom(query)
  const index = new Map(buckets.map((start, i) => [start, i]))
  const series = buckets.map(start => ({ start, operations: 0, deliveries: 0 }))
  const sources = dataSourcesOf(tenant)

  // Operations per day on each connection
  let operations = 0
  let operationsBefore = 0
  const connections: DataDashboard['connections'] = []
  const latencies: number[] = []
  for (const source of sources) {
    let own = 0
    for (const [day, count] of Object.entries(source.ops)) {
      const time = Date.parse(day)
      if (time >= from && time <= end) {
        own += count
        const i = index.get(iso(bucketStart(time, group)))
        if (i !== undefined) series[i]!.operations += count
      } else if (time >= prevFrom && time < from) operationsBefore += count
    }
    operations += own
    const check = checksOf(source, 1)[0]
    if (check?.latency_ms != null) latencies.push(check.latency_ms)
    connections.push({ id: source.id, name: source.name, engine: source.engine, status: statusOf(source), latency_ms: check?.latency_ms ?? null, last_checked_at: check?.at ?? null, operations: own })
  }

  // Responses stored in the workspace's databases
  const forms = new Map(formsOf(tenant).forms.map(form => [form.id, form]))
  const storage = { forms: 0, sent: 0, pending: 0, failed: 0 }
  let deliveriesBefore = 0
  for (const destination of destinationsOf(tenant)) {
    const form = forms.get(destination.form_id)
    if (!form || form.deleted_at) continue
    storage.forms++
    for (const delivery of deliveriesOf(tenant, destination, form)) {
      if (delivery.status === 'pending' || delivery.status === 'held') storage.pending++
      if (delivery.status === 'failed') storage.failed++
      if (delivery.status !== 'sent' || !delivery.at) continue
      const time = Date.parse(delivery.at)
      if (time >= from && time <= end) {
        storage.sent++
        const i = index.get(iso(bucketStart(time, group)))
        if (i !== undefined) series[i]!.deliveries++
      } else if (time >= prevFrom && time < from) deliveriesBefore++
    }
  }

  // What people did (the audit trail's data area)
  const data = auditLogOf(tenant).filter(item => item.area === 'data')
  const kinds = Object.fromEntries(ACTIVITY_KINDS.map(kind => [kind, 0])) as DataDashboard['kinds']
  for (const item of data) {
    const time = Date.parse(item.occurred_at)
    if (time < from || time > end) continue
    const kind = kindOfAction(item.action)
    if (kind) kinds[kind]++
  }
  const recent = data
    .slice()
    .sort((a, b) => Date.parse(b.occurred_at) - Date.parse(a.occurred_at))
    .slice(0, 6)
    .map(item => ({ id: item.id, action: item.action, actor: item.actor.name ?? '', resource: item.resource?.name ?? null, at: item.occurred_at }))

  const result: DataDashboard = {
    from: iso(from),
    to: iso(to),
    group,
    kpis: {
      connections: { value: sources.length, previous: null },
      operations: { value: operations, previous: operationsBefore },
      deliveries: { value: storage.sent, previous: deliveriesBefore },
      failing: { value: sources.filter(source => statusOf(source) === 'failing').length, previous: null },
      latency: { value: latencies.length ? Math.round(latencies.reduce((sum, n) => sum + n, 0) / latencies.length) : 0, previous: null },
    },
    series,
    connections: connections.sort((a, b) => (a.status === 'failing' ? -1 : 0) - (b.status === 'failing' ? -1 : 0) || b.operations - a.operations).slice(0, 8),
    kinds,
    storage,
    recent,
  }
  return ok(result)
})

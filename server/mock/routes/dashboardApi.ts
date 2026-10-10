/**
 * Dashboard, API service view (F21 M4, docs/API-CONTRACT.md → Dashboard): the API service at work. Needs
 * `api.view` (else FRM-PERM-1001).
 *
 *   GET /dashboard/api?from&to&group → ApiDashboard
 */
import type { ApiDashboard } from '#shared/types/dashboard'
import { bucketStart } from '#shared/utils/dashboard/buckets'
import { requireAuth } from '../core/auth'
import { MockError, ok } from '../core/respond'
import { defineMockRoute } from '../core/route'
import { apiOf } from '../data/apiStore'
import { logsOf } from '../data/apiTraffic'
import { integrationsOf } from '../data/integrationStore'
import { permissionsOf } from '../data/rolesStore'
import { periodFrom } from './dashboard'

const iso = (time: number) => new Date(time).toISOString().slice(0, 10)

export const apiDashboard = defineMockRoute(({ event, query }) => {
  const { tenant, user } = requireAuth(event)
  if (!permissionsOf(user, tenant).has('api.view')) throw new MockError('FRM-PERM-1001')
  const { from, to, group, prevFrom, end, buckets } = periodFrom(query)
  const index = new Map(buckets.map((start, i) => [start, i]))
  const series = buckets.map(start => ({ start, calls: 0, errors: 0 }))

  let calls = 0
  let callsBefore = 0
  let errors = 0
  let errorsBefore = 0
  let duration = 0
  let durationBefore = 0
  const statuses = { ok: 0, client: 0, server: 0 }
  const endpoints = new Map<string, ApiDashboard['endpoints'][number] & { total_ms: number }>()
  const tokenCalls = new Map<string, number>()
  const tokenLast = new Map<string, string>()
  const failed: ApiDashboard['errors'] = []
  for (const log of logsOf(tenant, prevFrom, end)) {
    const time = Date.parse(log.at)
    const bad = log.status >= 400
    if (time < from) {
      callsBefore++
      durationBefore += log.duration_ms
      if (bad) errorsBefore++
      continue
    }
    calls++
    duration += log.duration_ms
    if (bad) errors++
    if (log.status >= 500) statuses.server++
    else if (bad) statuses.client++
    else statuses.ok++
    const i = index.get(iso(bucketStart(time, group)))
    if (i !== undefined) {
      series[i]!.calls++
      if (bad) series[i]!.errors++
    }
    if (log.endpoint) {
      const row = endpoints.get(log.endpoint.id) ?? {
        id: log.endpoint.id,
        name: log.endpoint.name,
        service: log.service?.name ?? null,
        calls: 0,
        errors: 0,
        latency_ms: 0,
        total_ms: 0,
      }
      row.calls++
      row.total_ms += log.duration_ms
      if (bad) row.errors++
      endpoints.set(log.endpoint.id, row)
    }
    if (log.token) {
      tokenCalls.set(log.token.id, (tokenCalls.get(log.token.id) ?? 0) + 1)
      if (log.at > (tokenLast.get(log.token.id) ?? '')) tokenLast.set(log.token.id, log.at)
    }
    if (bad)
      failed.push({
        id: log.id,
        at: log.at,
        method: log.method,
        path: log.path,
        status: log.status,
        code: log.code,
      })
  }

  const api = apiOf(tenant)
  const now = Date.now()
  const tokens = api.tokens
    .filter(token => !token.revoked_at && (!token.expires_at || Date.parse(token.expires_at) > now))
    .map(token => ({
      id: token.id,
      name: token.name,
      mode: token.mode,
      calls: tokenCalls.get(token.id) ?? 0,
      last_used_at: [tokenLast.get(token.id), token.last_used_at].filter(Boolean).sort().pop() ?? null,
      expires_at: token.expires_at,
    }))
    .sort((a, b) => b.calls - a.calls)
    .slice(0, 6)

  const { webhooks, deliveries } = integrationsOf(tenant)
  const hooks = { active: 0, failing: 0, paused: 0, delivered: 0, failed: 0 }
  for (const webhook of webhooks) {
    if (!webhook.enabled) hooks.paused++
    else if (webhook.consecutive_failures > 0) hooks.failing++
    else hooks.active++
  }
  let deliveredBefore = 0
  for (const delivery of deliveries) {
    if (delivery.test) continue
    const time = Date.parse(delivery.at)
    if (time >= from && time <= end) {
      if (delivery.status === 'delivered') hooks.delivered++
      else if (delivery.status === 'failed') hooks.failed++
    } else if (time >= prevFrom && time < from && delivery.status === 'delivered') deliveredBefore++
  }

  const rate = (good: number, total: number) => (total ? Math.round((good / total) * 1000) / 10 : 100)
  const result: ApiDashboard = {
    from: iso(from),
    to: iso(to),
    group,
    kpis: {
      calls: { value: calls, previous: callsBefore },
      success_rate: {
        value: rate(calls - errors, calls),
        previous: callsBefore ? rate(callsBefore - errorsBefore, callsBefore) : null,
      },
      latency: {
        value: calls ? Math.round(duration / calls) : 0,
        previous: callsBefore ? Math.round(durationBefore / callsBefore) : null,
      },
      errors: { value: errors, previous: errorsBefore },
      deliveries: { value: hooks.delivered, previous: deliveredBefore },
    },
    series,
    endpoints: [...endpoints.values()]
      .sort((a, b) => b.calls - a.calls)
      .slice(0, 8)
      .map(({ total_ms, ...row }) => ({
        ...row,
        latency_ms: row.calls ? Math.round(total_ms / row.calls) : 0,
      })),
    statuses,
    tokens,
    webhooks: hooks,
    errors: failed.sort((a, b) => Date.parse(b.at) - Date.parse(a.at)).slice(0, 6),
  }
  return ok(result)
})

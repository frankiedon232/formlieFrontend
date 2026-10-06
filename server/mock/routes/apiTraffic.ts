/**
 * Mock request logs and API analytics (F13 M4, docs/API-CONTRACT.md → API service). Admins only until F22.
 *
 *   GET /api-logs                 the log (from, to, q, sort, filter[endpoint|class|method|token|mode], page)
 *   GET /api-logs/insights        30 days: calls, errors, by status class, answer time
 *   GET /api-logs/settings · PUT  keep request / response bodies (personal answers masked)
 *   GET /api-logs/:id             one call, with headers (secrets masked) and kept bodies
 *   GET /api-analytics?period     7d | 30d: totals with the period before, per day, endpoints, tokens, countries, methods
 */
import { z } from 'zod'
import type { ApiAnalytics, ApiLogDetail, ApiLogEntry, ApiLogInsights, ApiLogSettings } from '#shared/types/apiService'
import { API_METHODS, type ApiMethod } from '#shared/utils/urls/public'
import { actorOf, recordAudit } from '../core/audit'
import { requireAdmin } from '../core/auth'
import { filtersOf, MockError, ok, paginate } from '../core/respond'
import { defineMockRoute } from '../core/route'
import { parseBody } from '../core/validate'
import { apiOf, endpointUsage, saveApi } from '../data/apiStore'
import { logById, logsOf, realLogsOf, type StoredLog } from '../data/apiTraffic'
import { seedOf } from '../data/dataSourceSim'
import type { MockTenant } from '../data/tenants'

const DAY = 86_400_000
const listOf = (value: string | undefined) => (value ? value.split(',') : [])
const classOf = (status: number) => (status >= 500 ? '5xx' : status >= 400 ? '4xx' : '2xx')
const entry = ({ request_body: _a, response_body: _b, request_headers: _c, ...rest }: StoredLog): ApiLogEntry => rest
const day = (time: number) => new Date(time).toISOString().slice(0, 10)
const settingsOf = (tenant: MockTenant): ApiLogSettings => apiOf(tenant).logging ?? { keep_bodies: false, days: 7 }

export const listApiLogs = defineMockRoute(({ event, query }) => {
  const { tenant } = requireAdmin(event)
  const filter = filtersOf(query)
  const from = typeof query.from === 'string' && query.from ? Date.parse(`${query.from}T00:00:00Z`) : Date.now() - 7 * DAY
  const to = typeof query.to === 'string' && query.to ? Date.parse(`${query.to}T23:59:59Z`) : Date.now()
  let rows = logsOf(tenant, from, to)
  if (filter.endpoint) rows = rows.filter(row => row.endpoint && listOf(filter.endpoint).includes(row.endpoint.id))
  if (filter.class) rows = rows.filter(row => listOf(filter.class).includes(classOf(row.status)))
  if (filter.method) rows = rows.filter(row => listOf(filter.method).includes(row.method))
  if (filter.token) rows = rows.filter(row => row.token && listOf(filter.token).includes(row.token.id))
  if (filter.mode) rows = rows.filter(row => row.token && listOf(filter.mode).includes(row.token.mode))
  const sort = typeof query.sort === 'string' && query.sort ? query.sort : '-at'
  if (sort !== '-at') {
    const desc = sort.startsWith('-')
    const key = (desc ? sort.slice(1) : sort) as 'at' | 'duration_ms' | 'status'
    rows = [...rows].sort((a, b) => {
      const order = typeof a[key] === 'number' ? (a[key] as number) - (b[key] as number) : String(a[key]).localeCompare(String(b[key]))
      return desc ? -order : order
    })
  }
  const { data, meta } = paginate(rows.map(entry), { ...query, sort: undefined }, (row, q) => `${row.path} ${row.ip} ${row.request_id} ${row.code ?? ''} ${row.token?.name ?? ''}`.toLowerCase().includes(q))
  return ok(data, meta)
})

export const apiLogInsights = defineMockRoute(({ event }) => {
  const { tenant } = requireAdmin(event)
  const api = apiOf(tenant)
  const usages = api.endpoints.map(item => endpointUsage(tenant, item))
  const real = realLogsOf(tenant).filter(item => Date.parse(item.at) > Date.now() - 30 * DAY)
  const daily = (usages[0]?.daily ?? Array.from({ length: 30 }, (_, i) => ({ date: day(Date.now() - (29 - i) * DAY), count: 0 }))).map((item, i) => ({
    date: item.date,
    count: usages.reduce((sum, usage) => sum + (usage.daily[i]?.count ?? 0), 0) + real.filter(log => log.at.startsWith(item.date)).length,
  }))
  const calls = daily.reduce((sum, item) => sum + item.count, 0)
  const errors = usages.reduce((sum, usage) => sum + usage.errors_30d, 0) + real.filter(log => log.status >= 400).length
  const fiveXx = Math.round(errors * 0.06) + real.filter(log => log.status >= 500).length
  const times = usages.map(usage => usage.avg_ms).filter((n): n is number => n != null)
  const insights: ApiLogInsights = {
    calls_30d: calls,
    previous_30d: usages.reduce((sum, usage) => sum + usage.previous_30d, 0),
    errors_30d: errors,
    daily,
    by_class: { '2xx': Math.max(0, calls - errors), '4xx': Math.max(0, errors - fiveXx), '5xx': fiveXx },
    avg_ms: times.length ? Math.round(times.reduce((sum, n) => sum + n, 0) / times.length) : null,
  }
  return ok(insights)
})

export const getApiLogSettings = defineMockRoute(({ event }) => {
  const { tenant } = requireAdmin(event)
  return ok(settingsOf(tenant))
})

export const updateApiLogSettings = defineMockRoute(({ event, body }) => {
  const { tenant, user } = requireAdmin(event)
  const values = parseBody(z.object({ keep_bodies: z.boolean(), days: z.number().int().refine(n => [1, 7, 30].includes(n)) }), body)
  const before = settingsOf(tenant)
  apiOf(tenant).logging = values
  saveApi()
  recordAudit(event, tenant, { action: 'api.logging_changed', actor: actorOf(user), resource: { type: 'api_service', id: null, name: 'Request log' }, changes: [{ field: 'keep_bodies', before: before.keep_bodies, after: values.keep_bodies }, ...(before.days !== values.days ? [{ field: 'days', before: before.days, after: values.days }] : [])] })
  return ok(values)
})

export const getApiLog = defineMockRoute(({ event }) => {
  const { tenant } = requireAdmin(event)
  const found = logById(tenant, getRouterParam(event, 'id') ?? '')
  if (!found) throw new MockError('FRM-GEN-1004')
  const kept = found.request_body !== null || found.response_body !== null
  const detail: ApiLogDetail = { ...entry(found), request_body: found.request_body, response_body: found.response_body, request_headers: found.request_headers, bodies_kept: kept }
  return ok(detail)
})

export const apiAnalytics = defineMockRoute(({ event, query }) => {
  const { tenant } = requireAdmin(event)
  const api = apiOf(tenant)
  const days = query.period === '7d' ? 7 : 30
  const usages = api.endpoints.map(endpoint => ({ endpoint, usage: endpointUsage(tenant, endpoint) }))
  const window = (list: { count: number }[], offset: number) => list.slice(30 - offset - days, 30 - offset).reduce((sum, item) => sum + item.count, 0)
  const callsOf = (usage: (typeof usages)[number]['usage']) => window(usage.daily, 0)
  const previousOf = (usage: (typeof usages)[number]['usage']) => (days === 7 ? window(usage.daily, 7) : usage.previous_30d)
  const errorsOf = (usage: (typeof usages)[number]['usage'], calls: number) => (usage.calls_30d ? Math.round((usage.errors_30d / usage.calls_30d) * calls) : 0)
  const totalCalls = usages.reduce((sum, item) => sum + callsOf(item.usage), 0)
  const totalPrevious = usages.reduce((sum, item) => sum + previousOf(item.usage), 0)
  const totalErrors = usages.reduce((sum, item) => sum + errorsOf(item.usage, callsOf(item.usage)), 0)
  const times = usages.map(item => item.usage.avg_ms).filter((n): n is number => n != null)
  const avg = times.length ? times.reduce((sum, n) => sum + n, 0) / times.length : null
  const live = api.tokens.filter(token => !token.revoked_at)
  const weights = live.map(token => 1 + (seedOf(token.id) % 9))
  const weightSum = weights.reduce((sum, n) => sum + n, 0) || 1
  const sample = logsOf(tenant)
  const countryCounts = new Map<string, number>()
  for (const log of sample) if (log.country) countryCounts.set(log.country, (countryCounts.get(log.country) ?? 0) + 1)
  const sampleTotal = [...countryCounts.values()].reduce((sum, n) => sum + n, 0) || 1
  const methods = Object.fromEntries(API_METHODS.map(method => [method, 0])) as Record<ApiMethod, number>
  for (const { endpoint, usage } of usages) {
    const calls = callsOf(usage)
    endpoint.methods.forEach((method, i) => (methods[method] += Math.round((calls * (i === 0 ? 0.6 : 0.4 / Math.max(1, endpoint.methods.length - 1))) / (endpoint.methods.length === 1 ? 0.6 : 1))))
  }
  const analytics: ApiAnalytics = {
    from: day(Date.now() - (days - 1) * DAY),
    to: day(Date.now()),
    totals: { calls: totalCalls, errors: totalErrors, p50_ms: avg ? Math.round(avg * 0.85) : null, p95_ms: avg ? Math.round(avg * 2.4) : null, tokens_used: live.filter(token => token.last_used_at && Date.parse(token.last_used_at) > Date.now() - days * DAY).length },
    previous: { calls: totalPrevious, errors: Math.round(totalPrevious * (totalCalls ? totalErrors / totalCalls : 0) * 1.08), p50_ms: avg ? Math.round(avg * 0.9) : null, p95_ms: avg ? Math.round(avg * 2.6) : null, tokens_used: Math.max(0, live.length - 1) },
    daily: Array.from({ length: days }, (_, i) => {
      const index = 30 - days + i
      const calls = usages.reduce((sum, item) => sum + (item.usage.daily[index]?.count ?? 0), 0)
      const errors = usages.reduce((sum, item) => sum + errorsOf(item.usage, item.usage.daily[index]?.count ?? 0), 0)
      return { date: usages[0]?.usage.daily[index]?.date ?? day(Date.now() - (days - 1 - i) * DAY), calls, errors }
    }),
    endpoints: usages
      .map(({ endpoint, usage }) => ({ id: endpoint.id, name: endpoint.name, service: api.services.find(item => item.id === endpoint.service_id)?.name ?? '', calls: callsOf(usage), errors: errorsOf(usage, callsOf(usage)), p95_ms: usage.avg_ms ? Math.round(usage.avg_ms * 2.4) : null, trend: usage.daily.slice(-days).map(item => item.count) }))
      .sort((a, b) => b.calls - a.calls),
    tokens: live.map((token, i) => {
      const calls = Math.round((totalCalls * weights[i]!) / weightSum)
      return { id: token.id, name: token.name, mode: token.mode, calls, errors: Math.round(calls * (totalCalls ? totalErrors / totalCalls : 0)) }
    }).sort((a, b) => b.calls - a.calls),
    countries: [...countryCounts].map(([code, count]) => ({ code, calls: Math.round((totalCalls * count) / sampleTotal) })).sort((a, b) => b.calls - a.calls).slice(0, 10),
    methods,
  }
  return ok(analytics)
})

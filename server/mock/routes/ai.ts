/**
 * Mock AI assistant (F19 M1, docs/API-CONTRACT.md → AI assistant): settings, usage and the history of requests.
 *
 *   GET    /ai/settings             the workspace's settings (ai.use)
 *   PATCH  /ai/settings             { enabled?, sources?, mask_personal?, keep_days? } (ai.settings)
 *   GET    /ai/usage                this month's credits, by day and kind (ai.use)
 *   GET    /ai/requests             list (q, sort, filter[kind|status|person]); yours, or everyone's with ai.settings (ai.history)
 *   GET    /ai/requests/insights    counts for the two chart cards (same reach as the list)
 *   GET    /ai/requests/:id         one, with the prompt and the result
 *   DELETE /ai/requests/:id         yours, or any with ai.settings
 */
import { z } from 'zod'
import { AI_KEEP_DAYS, AI_SOURCES, type AiRequestInsights, type AiUsage } from '#shared/types/ai'
import { actorOf, recordAudit } from '../core/audit'
import { requireAuth } from '../core/auth'
import { MockError, filtersOf, ok, paginate } from '../core/respond'
import { defineMockRoute } from '../core/route'
import { parseBody } from '../core/validate'
import { aiOf, allowanceOf, creditsUsed, emptyByKind, emptyByStatus, monthStart, saveAi, toAiDetail, toAiRow, type StoredAiRequest } from '../data/aiStore'
import { permissionsOf } from '../data/rolesStore'
import { settingsOf } from '../data/settingsStore'
import type { MockTenant, MockUser } from '../data/tenants'

const DAY = 86_400_000
const isoDay = (time: number) => new Date(time).toISOString().slice(0, 10)
const lastDays = (count: number, value: (date: string) => number) =>
  Array.from({ length: count }, (_, index) => {
    const date = isoDay(Date.now() - (count - 1 - index) * DAY)
    return { date, count: value(date) }
  })

/** Everyone sees their own requests; whoever manages the assistant sees the workspace's. */
const visible = (tenant: MockTenant, user: MockUser): StoredAiRequest[] => {
  const all = aiOf(tenant).requests
  return permissionsOf(user, tenant).has('ai.settings') ? all : all.filter(request => request.by.id === user.id)
}

const withBrand = (tenant: MockTenant) => ({ ...aiOf(tenant).settings, brand_color: settingsOf(tenant).branding.brand_color })

export const getAiSettings = defineMockRoute(({ event }) => {
  const { tenant } = requireAuth(event)
  return ok(withBrand(tenant))
})

const settingsInput = z.object({
  enabled: z.boolean().optional(),
  sources: z.object({ forms: z.boolean(), responses: z.boolean(), data: z.boolean() }).partial().optional(),
  mask_personal: z.boolean().optional(),
  keep_days: z.literal(AI_KEEP_DAYS).optional(),
})

export const updateAiSettings = defineMockRoute(({ event, body }) => {
  const { tenant, user } = requireAuth(event)
  const values = parseBody(settingsInput, body)
  const store = aiOf(tenant)
  const before = structuredClone(store.settings)
  const settings = store.settings
  if (values.enabled !== undefined) settings.enabled = values.enabled
  if (values.sources) Object.assign(settings.sources, values.sources)
  if (values.mask_personal !== undefined) settings.mask_personal = values.mask_personal
  if (values.keep_days !== undefined) settings.keep_days = values.keep_days
  settings.updated_at = new Date().toISOString()
  settings.updated_by = { id: user.id, name: `${user.first_name} ${user.last_name}`.trim() }
  saveAi()
  const changed = Object.fromEntries(
    (['enabled', 'mask_personal', 'keep_days'] as const).filter(key => before[key] !== settings[key]).map(key => [key, `${before[key]} → ${settings[key]}`]),
  )
  for (const source of AI_SOURCES) if (before.sources[source] !== settings.sources[source]) changed[`reads_${source}`] = `${before.sources[source]} → ${settings.sources[source]}`
  recordAudit(event, tenant, { action: before.enabled !== settings.enabled ? (settings.enabled ? 'ai.enabled' : 'ai.disabled') : 'ai.settings_updated', actor: actorOf(user), resource: { type: 'setting', id: 'ai', name: 'AI assistant' }, metadata: changed })
  return ok(withBrand(tenant))
})

export const getAiUsage = defineMockRoute(({ event }) => {
  const { tenant } = requireAuth(event)
  const store = aiOf(tenant)
  const start = monthStart()
  const end = new Date(Date.UTC(start.getUTCFullYear(), start.getUTCMonth() + 1, 0))
  const thisMonth = store.requests.filter(request => Date.parse(request.created_at) >= start.getTime())
  // The month before, over the same number of days, for the change
  const elapsed = Date.now() - start.getTime()
  const prevStart = new Date(Date.UTC(start.getUTCFullYear(), start.getUTCMonth() - 1, 1)).getTime()
  const previous = store.requests.filter(request => Date.parse(request.created_at) >= prevStart && Date.parse(request.created_at) < prevStart + elapsed).reduce((sum, request) => sum + request.credits, 0)
  const byKind = emptyByKind()
  for (const request of thisMonth) byKind[request.kind] += request.credits
  const usage: AiUsage = {
    period: { start: start.toISOString().slice(0, 10), end: end.toISOString().slice(0, 10) },
    used: creditsUsed(tenant),
    limit: allowanceOf(tenant),
    previous,
    requests: thisMonth.length,
    people: new Set(thisMonth.map(request => request.by.id)).size,
    daily: lastDays(30, date => store.requests.filter(request => request.created_at.startsWith(date)).reduce((sum, request) => sum + request.credits, 0)),
    by_kind: byKind,
  }
  return ok(usage)
})

export const listAiRequests = defineMockRoute(({ event, query }) => {
  const { tenant, user } = requireAuth(event)
  const filter = filtersOf(query)
  let rows = visible(tenant, user)
  if (filter.kind) rows = rows.filter(row => filter.kind!.split(',').includes(row.kind))
  if (filter.status) rows = rows.filter(row => filter.status!.split(',').includes(row.status))
  if (filter.person) rows = rows.filter(row => filter.person!.split(',').includes(row.by.id))
  if (typeof query.from === 'string' && query.from) rows = rows.filter(row => row.created_at.slice(0, 10) >= (query.from as string))
  if (typeof query.to === 'string' && query.to) rows = rows.filter(row => row.created_at.slice(0, 10) <= (query.to as string))
  const sort = typeof query.sort === 'string' && query.sort ? query.sort : '-created_at'
  const desc = sort.startsWith('-')
  const key = (desc ? sort.slice(1) : sort) as 'created_at' | 'credits' | 'title'
  const sorted = [...rows].sort((a, b) => {
    const order = key === 'credits' ? a.credits - b.credits : String(a[key]).localeCompare(String(b[key]), undefined, { numeric: true })
    return desc ? -order : order
  })
  const { data, meta } = paginate(
    sorted.map(row => toAiRow(row, user)),
    { ...query, sort: undefined },
    (row, q) => `${row.title} ${row.by.name} ${row.target?.name ?? ''}`.toLowerCase().includes(q.toLowerCase()),
  )
  return ok(data, meta)
})

export const aiRequestInsights = defineMockRoute(({ event }) => {
  const { tenant, user } = requireAuth(event)
  const rows = visible(tenant, user)
  const since = Date.now() - 30 * DAY
  const recent = rows.filter(row => Date.parse(row.created_at) >= since)
  const byStatus = emptyByStatus()
  const byKind = emptyByKind()
  for (const row of rows) {
    byStatus[row.status] += 1
    byKind[row.kind] += 1
  }
  const insights: AiRequestInsights = {
    total: recent.length,
    previous: rows.filter(row => Date.parse(row.created_at) >= since - 30 * DAY && Date.parse(row.created_at) < since).length,
    daily: lastDays(30, date => rows.filter(row => row.created_at.startsWith(date)).length),
    by_status: byStatus,
    by_kind: byKind,
    people: new Set(recent.map(row => row.by.id)).size,
    credits: recent.reduce((sum, row) => sum + row.credits, 0),
  }
  return ok(insights)
})

function find(tenant: MockTenant, user: MockUser, id: string | undefined) {
  const request = visible(tenant, user).find(item => item.id === id)
  if (!request) throw new MockError('FRM-GEN-1004')
  return request
}

export const getAiRequest = defineMockRoute(({ event }) => {
  const { tenant, user } = requireAuth(event)
  return ok(toAiDetail(tenant, find(tenant, user, getRouterParam(event, 'id')), user))
})

export const deleteAiRequest = defineMockRoute(({ event }) => {
  const { tenant, user } = requireAuth(event)
  const request = find(tenant, user, getRouterParam(event, 'id'))
  const store = aiOf(tenant)
  store.requests.splice(store.requests.indexOf(request), 1)
  saveAi()
  recordAudit(event, tenant, { action: 'ai.request_deleted', actor: actorOf(user), resource: { type: 'ai_request', id: request.id, name: request.title }, metadata: { kind: request.kind, by: request.by.name } })
  return ok({ deleted: true })
})

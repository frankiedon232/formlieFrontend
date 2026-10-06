/**
 * Mock API access rules and rate limits (F13 M3, docs/API-CONTRACT.md → API service). Admins only until F22.
 *
 *   GET    /api-access-rules              list (q, sort, filter[action|kind|scope]) · /insights · /:id
 *   POST   /api-access-rules              { action, kind, values, scope, note?, enabled? } · PATCH · DELETE
 *   POST   /api-access-rules/test         would this caller get in (endpoint, IP, origin, country)?
 *   GET    /api-service/limits            calls per minute per token, IP and endpoint · PUT
 */
import { z } from 'zod'
import type { ApiAccessInsights, ApiAccessTestResult, ApiRateLimits } from '#shared/types/apiService'
import { API_NETWORKS, API_RULE_KINDS } from '#shared/types/apiService'
import { checkRuleValue, decideAccess, normaliseRuleValue, regionOf, rulesFor } from '#shared/utils/apiService/access'
import { actorOf, recordAudit } from '../core/audit'
import { requireAdmin } from '../core/auth'
import { filtersOf, MockError, ok, paginate } from '../core/respond'
import { defineMockRoute } from '../core/route'
import { parseBody } from '../core/validate'
import { apiOf, saveApi, toRule, type StoredAccessRule } from '../data/apiStore'
import type { MockTenant } from '../data/tenants'

const DAY = 86_400_000
const ruleInput = z.object({
  action: z.enum(['allow', 'block']),
  kind: z.enum(API_RULE_KINDS),
  values: z.array(z.string().trim().max(255)).min(1).max(50),
  scope: z.object({ type: z.enum(['all', 'service', 'endpoint']), id: z.string().nullable() }),
  note: z.string().trim().max(300).nullish(),
  enabled: z.boolean().optional(),
})
const limit = z.number().int().min(1).max(100_000).nullable()

function findRule(tenant: MockTenant, id: string | undefined) {
  const rule = apiOf(tenant).rules.find(item => item.id === id)
  if (!rule) throw new MockError('FRM-GEN-1004')
  return rule
}
/** Values checked per kind (duplicates dropped), the scope naming a service or endpoint of this organisation. */
function checked(tenant: MockTenant, values: z.infer<typeof ruleInput>) {
  const problems = values.values.map((value, index) => ({ index, problem: checkRuleValue(values.kind, value) })).filter(item => item.problem)
  if (problems.length) throw new MockError('FRM-GEN-1002', problems.map(item => ({ field: `values.${item.index}`, message: item.problem! })))
  const api = apiOf(tenant)
  const scope = values.scope.type === 'all' ? { type: 'all' as const, id: null } : values.scope
  if (scope.type === 'service' && !api.services.some(item => item.id === scope.id)) throw new MockError('FRM-GEN-1002', [{ field: 'scope', message: 'service' }])
  if (scope.type === 'endpoint' && !api.endpoints.some(item => item.id === scope.id)) throw new MockError('FRM-GEN-1002', [{ field: 'scope', message: 'endpoint' }])
  return { action: values.action, kind: values.kind, values: [...new Set(values.values.map(value => normaliseRuleValue(values.kind, value)))], scope, note: values.note || null }
}
const listOf = (value: string | undefined) => (value ? value.split(',') : [])

export const listAccessRules = defineMockRoute(({ event, query }) => {
  const { tenant } = requireAdmin(event)
  const filter = filtersOf(query)
  let rows = apiOf(tenant).rules.map(item => toRule(tenant, item))
  if (filter.action) rows = rows.filter(row => listOf(filter.action).includes(row.action))
  if (filter.kind) rows = rows.filter(row => listOf(filter.kind).includes(row.kind))
  if (filter.scope) rows = rows.filter(row => listOf(filter.scope).includes(row.scope.type))
  if (filter.state) rows = rows.filter(row => listOf(filter.state).includes(row.enabled ? 'on' : 'off'))
  const sort = typeof query.sort === 'string' && query.sort ? query.sort : '-created_at'
  const desc = sort.startsWith('-')
  const key = (desc ? sort.slice(1) : sort) as 'created_at' | 'hits_30d' | 'last_hit_at' | 'action'
  rows.sort((a, b) => {
    const x = a[key] ?? ''
    const y = b[key] ?? ''
    const order = typeof x === 'number' && typeof y === 'number' ? x - y : String(x).localeCompare(String(y))
    return desc ? -order : order
  })
  const { data, meta } = paginate(rows, { ...query, sort: undefined }, (row, q) => `${row.values.join(' ')} ${row.note ?? ''} ${row.scope.name ?? ''}`.toLowerCase().includes(q))
  return ok(data, meta)
})

export const accessInsights = defineMockRoute(({ event }) => {
  const { tenant } = requireAdmin(event)
  const api = apiOf(tenant)
  const rules = api.rules.map(item => toRule(tenant, item))
  const today = Date.parse(new Date().toISOString().slice(0, 10))
  const day = (offset: number) => new Date(today - offset * DAY).toISOString().slice(0, 10)
  const refused = (date: string) => api.rules.filter(rule => rule.action === 'block').reduce((sum, rule) => sum + (rule.hits[date] ?? 0), 0)
  const daily = Array.from({ length: 30 }, (_, i) => ({ date: day(29 - i), count: refused(day(29 - i)) }))
  const insights: ApiAccessInsights = {
    total: rules.length,
    by_action: { allow: rules.filter(rule => rule.action === 'allow').length, block: rules.filter(rule => rule.action === 'block').length },
    by_kind: Object.fromEntries(API_RULE_KINDS.map(kind => [kind, rules.filter(rule => rule.kind === kind).length])) as ApiAccessInsights['by_kind'],
    refused_30d: daily.reduce((sum, item) => sum + item.count, 0),
    previous_30d: Array.from({ length: 30 }, (_, i) => refused(day(30 + i))).reduce((sum, n) => sum + n, 0),
    daily,
    limited_30d: Array.from({ length: 30 }, (_, i) => api.limited[day(i)] ?? 0).reduce((sum, n) => sum + n, 0),
  }
  return ok(insights)
})

export const getAccessRule = defineMockRoute(({ event }) => {
  const { tenant } = requireAdmin(event)
  return ok(toRule(tenant, findRule(tenant, getRouterParam(event, 'id'))))
})

export const createAccessRule = defineMockRoute(({ event, body }) => {
  const { tenant, user } = requireAdmin(event)
  const values = parseBody(ruleInput, body)
  const now = new Date().toISOString()
  const rule: StoredAccessRule = { id: crypto.randomUUID(), ...checked(tenant, values), enabled: values.enabled ?? true, hits: {}, last_hit_at: null, created_by: { id: user.id, name: `${user.first_name} ${user.last_name}` }, created_at: now, updated_at: now }
  apiOf(tenant).rules.unshift(rule)
  saveApi()
  recordAudit(event, tenant, { action: 'api.rule_created', actor: actorOf(user), resource: { type: 'api_rule', id: rule.id, name: `${rule.action} ${rule.kind}` }, metadata: { values: rule.values.join(', ').slice(0, 300), scope: rule.scope.type } })
  return ok(toRule(tenant, rule), {}, 201)
})

export const updateAccessRule = defineMockRoute(({ event, body }) => {
  const { tenant, user } = requireAdmin(event)
  const rule = findRule(tenant, getRouterParam(event, 'id'))
  const only = z.object({ enabled: z.boolean() }).strict().safeParse(body)
  const resource = { type: 'api_rule', id: rule.id, name: `${rule.action} ${rule.kind}` }
  if (only.success) {
    if (rule.enabled !== only.data.enabled) {
      rule.enabled = only.data.enabled
      rule.updated_at = new Date().toISOString()
      saveApi()
      recordAudit(event, tenant, { action: rule.enabled ? 'api.rule_enabled' : 'api.rule_disabled', actor: actorOf(user), resource })
    }
    return ok(toRule(tenant, rule))
  }
  const values = parseBody(ruleInput, body)
  Object.assign(rule, checked(tenant, values), { enabled: values.enabled ?? rule.enabled, updated_at: new Date().toISOString() })
  saveApi()
  recordAudit(event, tenant, { action: 'api.rule_updated', actor: actorOf(user), resource, metadata: { values: rule.values.join(', ').slice(0, 300), scope: rule.scope.type } })
  return ok(toRule(tenant, rule))
})

export const deleteAccessRule = defineMockRoute(({ event }) => {
  const { tenant, user } = requireAdmin(event)
  const rule = findRule(tenant, getRouterParam(event, 'id'))
  const list = apiOf(tenant).rules
  list.splice(list.indexOf(rule), 1)
  saveApi()
  recordAudit(event, tenant, { action: 'api.rule_deleted', actor: actorOf(user), resource: { type: 'api_rule', id: rule.id, name: `${rule.action} ${rule.kind}` } })
  return ok({ deleted: true })
})

export const testAccess = defineMockRoute(({ event, body }) => {
  const { tenant } = requireAdmin(event)
  const values = parseBody(z.object({ endpoint_id: z.string(), ip: z.string().trim().max(64), origin: z.string().trim().max(255).nullish(), country: z.string().trim().max(2).nullish(), networks: z.array(z.enum(API_NETWORKS)).max(4).optional() }), body)
  if (checkRuleValue('ip', values.ip) || values.ip.includes('/')) throw new MockError('FRM-GEN-1002', [{ field: 'ip', message: 'ip' }])
  const api = apiOf(tenant)
  const endpoint = api.endpoints.find(item => item.id === values.endpoint_id)
  if (!endpoint) throw new MockError('FRM-GEN-1002', [{ field: 'endpoint_id', message: 'required' }])
  let domain: string | null = null
  if (values.origin) {
    try {
      domain = new URL(values.origin.includes('://') ? values.origin : `https://${values.origin}`).hostname.toLowerCase()
    } catch {
      throw new MockError('FRM-GEN-1002', [{ field: 'origin', message: 'domain' }])
    }
  }
  const country = values.country ? values.country.toUpperCase() : null
  const applies = rulesFor(api.rules, endpoint)
  const decision = decideAccess(applies, { ip: values.ip, domain, country, networks: values.networks ?? [] })
  const rule = decision.rule ? toRule(tenant, applies.find(item => item.id === decision.rule!.id)!) : null
  const result: ApiAccessTestResult = {
    allowed: decision.allowed,
    reason: decision.reason,
    rule: rule ? { id: rule.id, action: rule.action, value: decision.rule!.value, kind: rule.kind, scope: rule.scope } : null,
    checked: applies.filter(item => item.enabled).length,
    region: regionOf(country),
  }
  return ok(result)
})

export const getRateLimits = defineMockRoute(({ event }) => {
  const { tenant } = requireAdmin(event)
  return ok(apiOf(tenant).limits)
})

export const updateRateLimits = defineMockRoute(({ event, body }) => {
  const { tenant, user } = requireAdmin(event)
  const values = parseBody(z.object({ per_token: limit, per_ip: limit, per_endpoint: limit }), body)
  const api = apiOf(tenant)
  const before = api.limits
  const limits: ApiRateLimits = { ...values, updated_at: new Date().toISOString() }
  api.limits = limits
  saveApi()
  recordAudit(event, tenant, {
    action: 'api.limits_changed',
    actor: actorOf(user),
    resource: { type: 'api_service', id: null, name: 'Rate limits' },
    changes: (['per_token', 'per_ip', 'per_endpoint'] as const).filter(key => before[key] !== values[key]).map(key => ({ field: key, before: before[key], after: values[key] })),
  })
  return ok(limits)
})

/**
 * Mock API keys for Formalie's own management API (F13 M6, docs/API-CONTRACT.md → Integrations).
 * Admins only until F22. Keys are kept as a hash and a preview; the key itself is returned once.
 *
 *   GET    /api-keys                 list (q, sort, filter[status|scope]) · /insights · /:id
 *   POST   /api-keys                 { name, scopes, expires_at? } → { key, secret }
 *   PATCH  /api-keys/:id             { name, scopes }
 *   POST   /api-keys/:id/revoke      stops working at once
 *   DELETE /api-keys/:id             only once revoked or expired
 */
import { z } from 'zod'
import { API_KEY_SCOPES, type ApiKeyInsights, type ManagementKeyWithSecret } from '#shared/types/integrations'
import { actorOf, recordAudit } from '../core/audit'
import { requireAdmin } from '../core/auth'
import { filtersOf, MockError, ok, paginate } from '../core/respond'
import { defineMockRoute } from '../core/route'
import { parseBody } from '../core/validate'
import { hashKey, integrationsOf, keyPreview, keyStatusOf, newManagementKey, saveIntegrations, toManagementKey, type StoredManagementKey } from '../data/integrationStore'
import type { MockTenant } from '../data/tenants'

const DAY = 86_400_000
const input = z.object({ name: z.string().trim().min(1).max(80), scopes: z.array(z.enum(API_KEY_SCOPES)).min(1) })
const listOf = (value: string | undefined) => (value ? value.split(',') : [])
const resource = (key: StoredManagementKey) => ({ type: 'api_key', id: key.id, name: key.name })

function findKey(tenant: MockTenant, id: string | undefined) {
  const key = integrationsOf(tenant).keys.find(item => item.id === id)
  if (!key) throw new MockError('FRM-GEN-1004')
  return key
}

export const listApiKeys = defineMockRoute(({ event, query }) => {
  const { tenant } = requireAdmin(event)
  const filter = filtersOf(query)
  let rows = integrationsOf(tenant).keys.map(toManagementKey)
  if (filter.status) rows = rows.filter(row => listOf(filter.status).includes(row.status))
  if (filter.scope) rows = rows.filter(row => row.scopes.some(scope => listOf(filter.scope).includes(scope)))
  const sort = typeof query.sort === 'string' && query.sort ? query.sort : '-created_at'
  const desc = sort.startsWith('-')
  const key = (desc ? sort.slice(1) : sort) as 'created_at' | 'name' | 'calls_30d' | 'last_used_at' | 'expires_at'
  rows.sort((a, b) => {
    const x = a[key] ?? ''
    const y = b[key] ?? ''
    const order = typeof x === 'number' && typeof y === 'number' ? x - y : String(x).localeCompare(String(y))
    return desc ? -order : order
  })
  const { data, meta } = paginate(rows, { ...query, sort: undefined }, (row, q) => `${row.name} ${row.preview}`.toLowerCase().includes(q))
  return ok(data, meta)
})

export const apiKeyInsights = defineMockRoute(({ event }) => {
  const { tenant } = requireAdmin(event)
  const keys = integrationsOf(tenant).keys
  const day = (offset: number) => new Date(Date.now() - offset * DAY).toISOString().slice(0, 10)
  const callsOn = (date: string) => keys.reduce((sum, key) => sum + (key.calls[date] ?? 0), 0)
  const daily = Array.from({ length: 30 }, (_, i) => ({ date: day(29 - i), count: callsOn(day(29 - i)) }))
  const statuses = keys.map(keyStatusOf)
  const insights: ApiKeyInsights = {
    total: keys.length,
    by_status: { active: statuses.filter(s => s === 'active').length, expiring: statuses.filter(s => s === 'expiring').length, expired: statuses.filter(s => s === 'expired').length, revoked: statuses.filter(s => s === 'revoked').length },
    calls_30d: daily.reduce((sum, item) => sum + item.count, 0),
    previous_30d: Array.from({ length: 30 }, (_, i) => callsOn(day(30 + i))).reduce((sum, n) => sum + n, 0),
    unused_90d: keys.filter(key => !key.revoked_at && (!key.last_used_at || Date.parse(key.last_used_at) < Date.now() - 90 * DAY) && Date.parse(key.created_at) < Date.now() - 90 * DAY).length,
    daily,
  }
  return ok(insights)
})

export const getApiKey = defineMockRoute(({ event }) => {
  const { tenant } = requireAdmin(event)
  return ok(toManagementKey(findKey(tenant, getRouterParam(event, 'id'))))
})

export const createApiKey = defineMockRoute(({ event, body }) => {
  const { tenant, user } = requireAdmin(event)
  const values = parseBody(input.extend({ expires_at: z.string().datetime().nullish() }), body)
  if (values.expires_at && Date.parse(values.expires_at) <= Date.now()) throw new MockError('FRM-GEN-1002', [{ field: 'expires_at', message: 'future' }])
  const secret = newManagementKey()
  const key: StoredManagementKey = { id: crypto.randomUUID(), name: values.name, secret_hash: hashKey(secret), preview: keyPreview(secret), scopes: [...new Set(values.scopes)], expires_at: values.expires_at ?? null, last_used_at: null, last_used_ip: null, calls: {}, created_by: { id: user.id, name: `${user.first_name} ${user.last_name}` }, created_at: new Date().toISOString(), revoked_at: null }
  integrationsOf(tenant).keys.unshift(key)
  saveIntegrations()
  recordAudit(event, tenant, { action: 'integrations.api_key_created', actor: actorOf(user), resource: resource(key), metadata: { scopes: key.scopes.join(', '), expires: key.expires_at ?? 'never' } })
  const result: ManagementKeyWithSecret = { key: toManagementKey(key), secret }
  return ok(result, {}, 201)
})

export const updateApiKey = defineMockRoute(({ event, body }) => {
  const { tenant, user } = requireAdmin(event)
  const key = findKey(tenant, getRouterParam(event, 'id'))
  if (key.revoked_at) throw new MockError('FRM-API-1004')
  const values = parseBody(input, body)
  const before = { name: key.name, scopes: key.scopes.join(', ') }
  key.name = values.name
  key.scopes = [...new Set(values.scopes)]
  saveIntegrations()
  recordAudit(event, tenant, {
    action: 'integrations.api_key_updated',
    actor: actorOf(user),
    resource: resource(key),
    changes: [...(before.name !== key.name ? [{ field: 'name', before: before.name, after: key.name }] : []), ...(before.scopes !== key.scopes.join(', ') ? [{ field: 'scopes', before: before.scopes, after: key.scopes.join(', ') }] : [])],
  })
  return ok(toManagementKey(key))
})

export const revokeApiKey = defineMockRoute(({ event }) => {
  const { tenant, user } = requireAdmin(event)
  const key = findKey(tenant, getRouterParam(event, 'id'))
  if (!key.revoked_at) {
    key.revoked_at = new Date().toISOString()
    saveIntegrations()
    recordAudit(event, tenant, { action: 'integrations.api_key_revoked', actor: actorOf(user), resource: resource(key) })
  }
  return ok(toManagementKey(key))
})

export const deleteApiKey = defineMockRoute(({ event }) => {
  const { tenant, user } = requireAdmin(event)
  const keys = integrationsOf(tenant).keys
  const key = findKey(tenant, getRouterParam(event, 'id'))
  const status = keyStatusOf(key)
  if (status !== 'revoked' && status !== 'expired') throw new MockError('FRM-API-1005')
  keys.splice(keys.indexOf(key), 1)
  saveIntegrations()
  recordAudit(event, tenant, { action: 'integrations.api_key_deleted', actor: actorOf(user), resource: resource(key) })
  return ok({ deleted: true })
})

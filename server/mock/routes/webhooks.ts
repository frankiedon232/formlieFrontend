/**
 * Mock webhooks (F13 M6, docs/API-CONTRACT.md → Integrations). Admins only until F22.
 *
 *   GET    /webhooks                         list (q, sort, filter[status|event]) · /insights · /:id
 *   POST   /webhooks                         { name, url, events, form_ids, enabled? } → { webhook, secret } (secret once)
 *   PATCH  /webhooks/:id                     the same, or { enabled } alone · DELETE (its deliveries go too)
 *   POST   /webhooks/:id/rotate              a new secret → { webhook, secret }
 *   POST   /webhooks/:id/test                a "ping" delivery now → the delivery with the receiver's answer
 *   GET    /webhook-deliveries               (from, to, q, sort, filter[webhook|status|event]) · /:id
 *   POST   /webhook-deliveries/:id/resend    the same body again as a new delivery
 */
import { z } from 'zod'
import type { WebhookInsights, WebhookWithSecret } from '#shared/types/integrations'
import { WEBHOOK_EVENTS } from '#shared/types/integrations'
import { checkWebhookUrl, webhookStatusOf } from '#shared/utils/integrations/webhooks'
import { actorOf, recordAudit } from '../core/audit'
import { requireAdmin } from '../core/auth'
import { confirmPassword } from '../core/confirm'
import { encodeId } from '../core/ids'
import { filtersOf, MockError, ok, paginate } from '../core/respond'
import { defineMockRoute } from '../core/route'
import { parseBody } from '../core/validate'
import { formsOf } from '../data/formStore'
import { attempt, integrationsOf, newWebhookSecret, queueDelivery, resumeRetries, saveIntegrations, toDelivery, toDeliveryDetail, toWebhook, type StoredWebhook } from '../data/integrationStore'
import type { MockTenant } from '../data/tenants'

const DAY = 86_400_000
const input = z.object({
  name: z.string().trim().min(1).max(80),
  url: z.string().trim().max(2000),
  events: z.array(z.enum(WEBHOOK_EVENTS)).min(1),
  form_ids: z.array(z.string()).max(100),
  enabled: z.boolean().optional(),
})
const listOf = (value: string | undefined) => (value ? value.split(',') : [])

function findWebhook(tenant: MockTenant, id: string | undefined) {
  const webhook = integrationsOf(tenant).webhooks.find(item => item.id === id)
  if (!webhook) throw new MockError('FRM-GEN-1004')
  return webhook
}
/** The address checked like the portal does (http://localhost allowed while developing) and the forms belonging to this organisation. */
function checked(tenant: MockTenant, values: z.infer<typeof input>) {
  const problem = checkWebhookUrl(values.url, { allowLocal: import.meta.dev })
  if (problem) throw new MockError('FRM-GEN-1002', [{ field: 'url', message: problem }])
  const forms = formsOf(tenant).forms
  const unknown = values.form_ids.filter(id => !forms.some(form => form.id === id && !form.deleted_at))
  if (unknown.length) throw new MockError('FRM-GEN-1002', [{ field: 'form_ids', message: 'form' }])
  return { name: values.name, url: values.url.trim(), events: [...new Set(values.events)], form_ids: [...new Set(values.form_ids)] }
}
const resource = (webhook: StoredWebhook) => ({ type: 'webhook', id: webhook.id, name: webhook.name })

export const listWebhooks = defineMockRoute(({ event, query }) => {
  const { tenant } = requireAdmin(event)
  resumeRetries(tenant)
  const filter = filtersOf(query)
  let rows = integrationsOf(tenant).webhooks.map(item => toWebhook(tenant, item))
  if (filter.status) rows = rows.filter(row => listOf(filter.status).includes(row.status))
  if (filter.event) rows = rows.filter(row => row.events.some(item => listOf(filter.event).includes(item)))
  const sort = typeof query.sort === 'string' && query.sort ? query.sort : '-created_at'
  const desc = sort.startsWith('-')
  const key = (desc ? sort.slice(1) : sort) as 'created_at' | 'name' | 'deliveries_30d' | 'success_rate'
  rows.sort((a, b) => {
    const x = a[key] ?? -1
    const y = b[key] ?? -1
    const order = typeof x === 'number' && typeof y === 'number' ? x - y : String(x).localeCompare(String(y))
    return desc ? -order : order
  })
  const { data, meta } = paginate(rows, { ...query, sort: undefined }, (row, q) => `${row.name} ${row.url}`.toLowerCase().includes(q))
  return ok(data, meta)
})

export const webhookInsights = defineMockRoute(({ event }) => {
  const { tenant } = requireAdmin(event)
  const store = integrationsOf(tenant)
  const hooks = store.webhooks.map(item => ({ ...item, status: webhookStatusOf(item) }))
  const live = store.deliveries.filter(item => !item.test)
  const since = Date.now() - 30 * DAY
  const recent = live.filter(item => Date.parse(item.at) >= since)
  const previous = live.filter(item => Date.parse(item.at) >= since - 30 * DAY && Date.parse(item.at) < since)
  const finished = recent.filter(item => item.status !== 'retrying')
  const daily = Array.from({ length: 30 }, (_, i) => {
    const date = new Date(Date.now() - (29 - i) * DAY).toISOString().slice(0, 10)
    return { date, count: recent.filter(item => item.at.startsWith(date)).length }
  })
  const insights: WebhookInsights = {
    total: hooks.length,
    by_status: { active: hooks.filter(item => item.status === 'active').length, failing: hooks.filter(item => item.status === 'failing').length, paused: hooks.filter(item => item.status === 'paused').length },
    deliveries_30d: recent.length,
    previous_30d: previous.length,
    failed_30d: recent.filter(item => item.status === 'failed').length,
    success_rate: finished.length ? finished.filter(item => item.status === 'delivered').length / finished.length : null,
    daily,
  }
  return ok(insights)
})

export const getWebhook = defineMockRoute(({ event }) => {
  const { tenant } = requireAdmin(event)
  return ok(toWebhook(tenant, findWebhook(tenant, getRouterParam(event, 'id'))))
})

export const createWebhook = defineMockRoute(({ event, body }) => {
  const { tenant, user } = requireAdmin(event)
  const values = parseBody(input, body)
  const now = new Date().toISOString()
  const secret = newWebhookSecret()
  const webhook: StoredWebhook = { id: crypto.randomUUID(), ...checked(tenant, values), enabled: values.enabled ?? true, paused_reason: values.enabled === false ? 'manual' : null, secret, consecutive_failures: 0, created_by: { id: user.id, name: `${user.first_name} ${user.last_name}` }, created_at: now, updated_at: now }
  integrationsOf(tenant).webhooks.unshift(webhook)
  saveIntegrations()
  recordAudit(event, tenant, { action: 'integrations.webhook_created', actor: actorOf(user), resource: resource(webhook), metadata: { url: webhook.url, events: webhook.events.join(', ') } })
  const result: WebhookWithSecret = { webhook: toWebhook(tenant, webhook), secret }
  return ok(result, {}, 201)
})

export const updateWebhook = defineMockRoute(({ event, body }) => {
  const { tenant, user } = requireAdmin(event)
  const webhook = findWebhook(tenant, getRouterParam(event, 'id'))
  const only = z.object({ enabled: z.boolean() }).strict().safeParse(body)
  if (only.success) {
    if (webhook.enabled !== only.data.enabled) {
      webhook.enabled = only.data.enabled
      webhook.paused_reason = webhook.enabled ? null : 'manual'
      if (webhook.enabled) webhook.consecutive_failures = 0
      webhook.updated_at = new Date().toISOString()
      saveIntegrations()
      recordAudit(event, tenant, { action: webhook.enabled ? 'integrations.webhook_enabled' : 'integrations.webhook_disabled', actor: actorOf(user), resource: resource(webhook) })
    }
    return ok(toWebhook(tenant, webhook))
  }
  const values = parseBody(input, body)
  const before = { url: webhook.url, events: webhook.events.join(', ') }
  Object.assign(webhook, checked(tenant, values), { updated_at: new Date().toISOString() })
  if (values.enabled !== undefined && values.enabled !== webhook.enabled) {
    webhook.enabled = values.enabled
    webhook.paused_reason = values.enabled ? null : 'manual'
    if (values.enabled) webhook.consecutive_failures = 0
  }
  saveIntegrations()
  recordAudit(event, tenant, {
    action: 'integrations.webhook_updated',
    actor: actorOf(user),
    resource: resource(webhook),
    changes: [
      ...(before.url !== webhook.url ? [{ field: 'url', before: before.url, after: webhook.url }] : []),
      ...(before.events !== webhook.events.join(', ') ? [{ field: 'events', before: before.events, after: webhook.events.join(', ') }] : []),
    ],
  })
  return ok(toWebhook(tenant, webhook))
})

export const deleteWebhook = defineMockRoute(({ event }) => {
  const { tenant, user } = requireAdmin(event)
  const store = integrationsOf(tenant)
  const webhook = findWebhook(tenant, getRouterParam(event, 'id'))
  store.webhooks.splice(store.webhooks.indexOf(webhook), 1)
  store.deliveries = store.deliveries.filter(item => item.webhook_id !== webhook.id)
  saveIntegrations()
  recordAudit(event, tenant, { action: 'integrations.webhook_deleted', actor: actorOf(user), resource: resource(webhook) })
  return ok({ deleted: true })
})

export const rotateWebhookSecret = defineMockRoute(({ event }) => {
  const { tenant, user } = requireAdmin(event)
  const webhook = findWebhook(tenant, getRouterParam(event, 'id'))
  webhook.secret = newWebhookSecret()
  webhook.updated_at = new Date().toISOString()
  saveIntegrations()
  recordAudit(event, tenant, { action: 'integrations.webhook_secret_rotated', actor: actorOf(user), resource: resource(webhook) })
  const result: WebhookWithSecret = { webhook: toWebhook(tenant, webhook), secret: webhook.secret }
  return ok(result)
})

/** A "ping" with a sample of what a response event looks like; waits for the receiver's answer. */
export const testWebhook = defineMockRoute(async ({ event }) => {
  const { tenant } = requireAdmin(event)
  const webhook = findWebhook(tenant, getRouterParam(event, 'id'))
  const form = formsOf(tenant).forms.find(item => (!webhook.form_ids.length || webhook.form_ids.includes(item.id)) && !item.deleted_at)
  const body = {
    type: 'ping',
    created_at: new Date().toISOString(),
    test: true,
    data: { webhook: { id: encodeId(webhook.id), name: webhook.name, events: webhook.events }, form: form ? { id: encodeId(form.id), name: form.name } : null, response: { id: 'rsp_sample', status: 'new', channel: 'link', answers: { full_name: 'Alex Morgan', email: 'alex.morgan@example.com' } } },
  }
  const { delivery, done } = queueDelivery(tenant, webhook, { event: 'ping', test: true, form_id: form?.id ?? null, response_id: null, body, personal: new Set(['full_name', 'email']) }, event)
  await done
  return ok(toDeliveryDetail(tenant, delivery))
})

export const listDeliveries = defineMockRoute(({ event, query }) => {
  const { tenant } = requireAdmin(event)
  resumeRetries(tenant)
  const filter = filtersOf(query)
  const from = typeof query.from === 'string' && query.from ? Date.parse(`${query.from}T00:00:00Z`) : 0
  const to = typeof query.to === 'string' && query.to ? Date.parse(`${query.to}T23:59:59Z`) : Date.now() + DAY
  let rows = integrationsOf(tenant)
    .deliveries.filter(item => Date.parse(item.at) >= from && Date.parse(item.at) <= to)
    .map(item => toDelivery(tenant, item))
  if (filter.webhook) rows = rows.filter(row => listOf(filter.webhook).includes(row.webhook.id))
  if (filter.status) rows = rows.filter(row => listOf(filter.status).includes(row.status))
  if (filter.event) rows = rows.filter(row => listOf(filter.event).includes(row.event))
  const sort = typeof query.sort === 'string' && query.sort ? query.sort : '-at'
  const desc = sort.startsWith('-')
  const key = (desc ? sort.slice(1) : sort) as 'at' | 'attempts' | 'duration_ms'
  rows.sort((a, b) => {
    const x = a[key] ?? -1
    const y = b[key] ?? -1
    const order = typeof x === 'number' && typeof y === 'number' ? x - y : String(x).localeCompare(String(y))
    return desc ? -order : order
  })
  const { data, meta } = paginate(rows, { ...query, sort: undefined }, (row, q) => `${row.webhook.name} ${row.event} ${row.form?.name ?? ''} ${row.status_code ?? ''}`.toLowerCase().includes(q))
  return ok(data, meta)
})

export const getDelivery = defineMockRoute(({ event }) => {
  const { tenant } = requireAdmin(event)
  const delivery = integrationsOf(tenant).deliveries.find(item => item.id === getRouterParam(event, 'id'))
  if (!delivery) throw new MockError('FRM-GEN-1004')
  return ok(toDeliveryDetail(tenant, delivery))
})

/** Send again: a new delivery with the same body (retries included); waits for the first try. */
export const resendDelivery = defineMockRoute(async ({ event }) => {
  const { tenant, user } = requireAdmin(event)
  const store = integrationsOf(tenant)
  const source = store.deliveries.find(item => item.id === getRouterParam(event, 'id'))
  if (!source) throw new MockError('FRM-GEN-1004')
  const webhook = findWebhook(tenant, source.webhook_id)
  if (source.status === 'retrying' && source.body) {
    // Retry now instead of waiting for the next try
    source.next_retry_at = null
    await attempt(tenant, source, event)
    return ok(toDeliveryDetail(tenant, source))
  }
  const parsed = JSON.parse(source.body ?? source.logged_body) as Record<string, unknown>
  delete parsed.id
  const { delivery, done } = queueDelivery(tenant, webhook, { event: source.event, test: source.test, form_id: source.form_id, response_id: source.response_id, body: parsed, personal: new Set() }, event)
  delivery.logged_body = source.logged_body.replace(/"id":"evt_[^"]*"/, `"id":"evt_${encodeId(delivery.id)}"`)
  await done
  recordAudit(event, tenant, { action: 'integrations.webhook_resent', actor: actorOf(user), resource: resource(webhook), metadata: { event: source.event } })
  return ok(toDeliveryDetail(tenant, delivery))
})

/** POST /webhooks/:id/reveal { password }: the signing secret again, after the password. */
export const revealWebhookSecret = defineMockRoute(({ event, body }) => {
  const { tenant, user } = requireAdmin(event)
  const webhook = findWebhook(tenant, getRouterParam(event, 'id'))
  confirmPassword(user, (body as { password?: unknown } | null)?.password)
  recordAudit(event, tenant, { action: 'integrations.webhook_secret_revealed', actor: actorOf(user), resource: resource(webhook) })
  return ok({ secret: webhook.secret })
})

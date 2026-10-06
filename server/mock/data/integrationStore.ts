/**
 * Webhooks in the mock (F13 M6), kept in `.data/mock/integrations.json`.
 * Webhooks really call their address: each response event becomes a delivery, signed with the
 * webhook's secret, retried after 1, 5, 15, 60 and 360 minutes (timers in this process; due retries
 * are also picked up whenever the lists are read), and a webhook pauses itself after 20 failures in a
 * row. Delivery logs show the body with personal answers masked; the body as sent is kept for
 * retries and Send again (the real backend keeps it encrypted, 30 days). A few samples are seeded.
 */
import { createHash, createHmac, randomBytes } from 'node:crypto'
import type { H3Event } from 'h3'
import type { Webhook, WebhookAttempt, WebhookDelivery, WebhookDeliveryDetail, WebhookDeliveryStatus, WebhookEvent } from '#shared/types/integrations'
import { signedPayload, WEBHOOK_AUTO_PAUSE, WEBHOOK_RETRY_MINUTES, WEBHOOK_TIMEOUT_MS, webhookStatusOf } from '#shared/utils/integrations/webhooks'
import { allFields } from '#shared/utils/forms/build'
import { recordAudit } from '../core/audit'
import { encodeId } from '../core/ids'
import { maskAnswers, PERSONAL_TYPES } from '../core/mask'
import { loadPersisted, savePersisted } from '../core/persist'
import { seedOf } from './dataSourceSim'
import { formsOf, type StoredForm } from './formStore'
import { answersOf, findResponse } from './responseData'
import { schemaOf } from './apiStore'
import { MOCK_TENANTS, MOCK_USERS, type MockTenant } from './tenants'

export interface StoredWebhook {
  id: string
  name: string
  url: string
  events: WebhookEvent[]
  form_ids: string[]
  enabled: boolean
  paused_reason: 'manual' | 'failures' | null
  /** HMAC needs the secret itself: encrypted at rest by the real backend, plain in the mock. */
  secret: string
  consecutive_failures: number
  created_by: { id: string; name: string }
  created_at: string
  updated_at: string
}

export interface StoredDelivery {
  id: string
  webhook_id: string
  event: WebhookEvent | 'ping'
  test: boolean
  form_id: string | null
  response_id: string | null
  at: string
  status: WebhookDeliveryStatus
  next_retry_at: string | null
  /** What is sent (kept only while it may be retried) and the copy for the log (personal answers masked). */
  body: string | null
  logged_body: string
  request_headers: Record<string, string>
  response: { headers: Record<string, string>; body: string | null } | null
  history: WebhookAttempt[]
}

interface TenantIntegrations {
  webhooks: StoredWebhook[]
  deliveries: StoredDelivery[]
}

const DAY = 86_400_000
const MAX_DELIVERIES = 600
const stores = new Map<string, TenantIntegrations>(Object.entries(loadPersisted<Record<string, TenantIntegrations>>('integrations', {})))
export const saveIntegrations = () => savePersisted('integrations', () => Object.fromEntries(stores))
const iso = (time: number) => new Date(time).toISOString()
const dayOf = (time: number) => iso(time).slice(0, 10)

export const newWebhookSecret = () => `formalie_hook_${randomBytes(24).toString('base64url')}`
export const hashKey = (secret: string) => createHash('sha256').update(secret).digest('hex')
export const keyPreview = (secret: string) => `${/^formalie_[a-z]+_/.exec(secret)?.[0] ?? ''}…${secret.slice(-4)}`

export function integrationsOf(tenant: MockTenant): TenantIntegrations {
  let store = stores.get(tenant.id)
  if (!store) {
    store = seed(tenant)
    stores.set(tenant.id, store)
    saveIntegrations()
  }
  // API keys were folded into tokens (owner, 2026-10-06): saved keys are dropped
  if ('keys' in store) {
    delete (store as { keys?: unknown }).keys
    saveIntegrations()
  }
  return store
}

// ── Seeds ─────────────────────────────────────────────────────────────────────────────────────

function seed(tenant: MockTenant): TenantIntegrations {
  const owner = MOCK_USERS.find(user => user.tenant_id === tenant.id && user.role === 'owner') ?? MOCK_USERS.find(user => user.tenant_id === tenant.id)
  const by = { id: owner?.id ?? 'system', name: owner ? `${owner.first_name} ${owner.last_name}` : 'Formalie' }
  const forms = formsOf(tenant).forms.filter(form => !form.deleted_at && form.status === 'published')
  const samples = [
    { name: 'CRM sync', url: 'https://hooks.example.com/formalie/crm', events: ['response.created', 'response.updated'] as WebhookEvent[], form_ids: forms.slice(0, 2).map(form => form.id), enabled: true, failing: 0, rate: 0.98 },
    { name: 'Data warehouse', url: 'https://ingest.example.org/v2/events', events: ['response.created', 'response.status_changed', 'response.deleted'] as WebhookEvent[], form_ids: [], enabled: true, failing: 3, rate: 0.82 },
    { name: 'Old ticketing bridge', url: 'https://tickets.example.net/inbound', events: ['response.created'] as WebhookEvent[], form_ids: forms.slice(2, 3).map(form => form.id), enabled: false, failing: 0, rate: 0.9 },
  ]
  const webhooks: StoredWebhook[] = []
  const deliveries: StoredDelivery[] = []
  samples.forEach((sample, i) => {
    const created = Date.now() - (90 - i * 20) * DAY
    const webhook: StoredWebhook = { id: crypto.randomUUID(), name: sample.name, url: sample.url, events: sample.events, form_ids: sample.form_ids, enabled: sample.enabled, paused_reason: sample.enabled ? null : 'manual', secret: newWebhookSecret(), consecutive_failures: sample.failing, created_by: by, created_at: iso(created), updated_at: iso(created + DAY) }
    webhooks.push(webhook)
    // A month of made-up deliveries (no bodies to resend: they are samples)
    for (let d = 29; d >= 0; d--) {
      if (!sample.enabled && d < 12) continue
      const count = seedOf(`${webhook.id}:${d}`) % 7
      for (let n = 0; n < count; n++) {
        const at = Date.now() - d * DAY - (seedOf(`${webhook.id}:${d}:${n}`) % (DAY - 60_000))
        if (at > Date.now()) continue
        const ok = d === 0 && sample.failing ? n >= sample.failing : (seedOf(`${webhook.id}:${d}:${n}:ok`) % 100) / 100 < sample.rate
        const tries = ok ? 1 + (seedOf(`${webhook.id}:${d}:${n}:t`) % 6 === 0 ? 1 : 0) : WEBHOOK_RETRY_MINUTES.length + 1
        const event = sample.events[seedOf(`${webhook.id}:${d}:${n}:e`) % sample.events.length]!
        const form = forms[seedOf(`${webhook.id}:${d}:${n}:f`) % Math.max(1, forms.length)]
        deliveries.push(sampleDelivery(webhook, event, form ?? null, at, ok, tries, d === 0 && !ok))
      }
    }
  })
  deliveries.sort((a, b) => b.at.localeCompare(a.at))
  return { webhooks, deliveries: deliveries.slice(0, MAX_DELIVERIES) }
}

function sampleDelivery(webhook: StoredWebhook, event: WebhookEvent, form: StoredForm | null, at: number, ok: boolean, tries: number, retrying: boolean): StoredDelivery {
  const id = crypto.randomUUID()
  const codes = [500, 502, 503, 404, null]
  const failCode = codes[seedOf(`${id}:c`) % codes.length]!
  const history: WebhookAttempt[] = Array.from({ length: retrying ? Math.min(tries, 2) : tries }, (_, i) => {
    const last = i === tries - 1
    const good = ok && last
    const code = good ? 200 : failCode
    return { at: iso(at + (i ? WEBHOOK_RETRY_MINUTES.slice(0, i).reduce((sum, m) => sum + m, 0) * 60_000 : 0)), status_code: code, duration_ms: 80 + (seedOf(`${id}:${i}`) % 700), error: good ? null : code === null ? 'timeout' : `HTTP ${code}` }
  })
  const body = JSON.stringify({ id: `evt_${encodeId(id)}`, type: event, created_at: iso(at), test: false, data: { form: form ? { id: encodeId(form.id), name: form.name } : null, response: { id: encodeId(crypto.randomUUID()), status: 'new' } } })
  const lastAt = Date.parse(history[history.length - 1]!.at)
  return {
    id,
    webhook_id: webhook.id,
    event,
    test: false,
    form_id: form?.id ?? null,
    response_id: null,
    at: iso(at),
    status: ok ? 'delivered' : retrying ? 'retrying' : 'failed',
    next_retry_at: retrying ? iso(Math.max(Date.now() + 10 * 60_000, lastAt + WEBHOOK_RETRY_MINUTES[history.length - 1]! * 60_000)) : null,
    body: null,
    logged_body: body,
    request_headers: deliveryHeaders(event, id, Math.floor(at / 1000), '••••'),
    response: { headers: { 'content-type': ok ? 'application/json' : 'text/html' }, body: ok ? '{"received":true}' : null },
    history,
  }
}

// ── Views ─────────────────────────────────────────────────────────────────────────────────────

const daysBack = (n: number) => Array.from({ length: n }, (_, i) => dayOf(Date.now() - (n - 1 - i) * DAY))

export function toWebhook(tenant: MockTenant, webhook: StoredWebhook): Webhook {
  const store = integrationsOf(tenant)
  const forms = formsOf(tenant).forms
  const since = Date.now() - 30 * DAY
  const mine = store.deliveries.filter(item => item.webhook_id === webhook.id && !item.test)
  const recent = mine.filter(item => Date.parse(item.at) >= since)
  const finished = recent.filter(item => item.status !== 'retrying')
  const timed = recent.flatMap(item => item.history.map(attempt => attempt.duration_ms))
  const last = store.deliveries.find(item => item.webhook_id === webhook.id)
  const lastAttempt = last?.history[last.history.length - 1]
  return {
    id: webhook.id,
    name: webhook.name,
    url: webhook.url,
    events: webhook.events,
    forms: webhook.form_ids.map(id => ({ id, name: forms.find(form => form.id === id)?.name ?? '' })).filter(form => form.name),
    enabled: webhook.enabled,
    status: webhookStatusOf(webhook),
    paused_reason: webhook.enabled ? null : webhook.paused_reason,
    secret_preview: keyPreview(webhook.secret),
    deliveries_30d: recent.length,
    failed_30d: recent.filter(item => item.status === 'failed').length,
    success_rate: finished.length ? finished.filter(item => item.status === 'delivered').length / finished.length : null,
    avg_ms: timed.length ? Math.round(timed.reduce((sum, n) => sum + n, 0) / timed.length) : null,
    last_delivery: last && lastAttempt ? { at: lastAttempt.at, ok: last.status === 'delivered', status_code: lastAttempt.status_code } : null,
    consecutive_failures: webhook.consecutive_failures,
    daily: daysBack(30).map(date => ({ date, count: mine.filter(item => item.at.startsWith(date)).length })),
    created_by: webhook.created_by,
    created_at: webhook.created_at,
    updated_at: webhook.updated_at,
  }
}

export function toDelivery(tenant: MockTenant, delivery: StoredDelivery): WebhookDelivery {
  const store = integrationsOf(tenant)
  const webhook = store.webhooks.find(item => item.id === delivery.webhook_id)
  const form = delivery.form_id ? formsOf(tenant).forms.find(item => item.id === delivery.form_id) : undefined
  const last = delivery.history[delivery.history.length - 1]
  return {
    id: delivery.id,
    webhook: { id: delivery.webhook_id, name: webhook?.name ?? '', url: webhook?.url ?? '' },
    event: delivery.event,
    status: delivery.status,
    attempts: delivery.history.length,
    status_code: last?.status_code ?? null,
    duration_ms: last?.duration_ms ?? null,
    at: delivery.at,
    next_retry_at: delivery.next_retry_at,
    test: delivery.test,
    form: form ? { id: form.id, name: form.name } : null,
    response_id: delivery.response_id,
  }
}

export function toDeliveryDetail(tenant: MockTenant, delivery: StoredDelivery): WebhookDeliveryDetail {
  return { ...toDelivery(tenant, delivery), request: { headers: delivery.request_headers, body: delivery.logged_body }, response: delivery.response, history: delivery.history }
}

// ── Delivering ────────────────────────────────────────────────────────────────────────────────

function deliveryHeaders(event: WebhookEvent | 'ping', id: string, timestamp: number, signature: string): Record<string, string> {
  return {
    'Content-Type': 'application/json',
    'User-Agent': 'Formalie-Webhooks/1.0',
    'X-Formalie-Event': event,
    'X-Formalie-Delivery': `dlv_${encodeId(id)}`,
    'X-Formalie-Timestamp': String(timestamp),
    'X-Formalie-Signature': signature,
  }
}

const timers = new Map<string, ReturnType<typeof setTimeout>>()
function schedule(tenant: MockTenant, delivery: StoredDelivery, event: H3Event | null) {
  if (!delivery.next_retry_at || timers.has(delivery.id)) return
  const wait = Math.max(0, Date.parse(delivery.next_retry_at) - Date.now())
  timers.set(
    delivery.id,
    setTimeout(() => {
      timers.delete(delivery.id)
      if (delivery.status === 'retrying' && delivery.next_retry_at) void attempt(tenant, delivery, event)
    }, Math.min(wait, 2 ** 31 - 1)),
  )
}

/** Retries that came due while the dev server was down (or have no timer yet). */
export function resumeRetries(tenant: MockTenant) {
  for (const delivery of integrationsOf(tenant).deliveries) if (delivery.status === 'retrying' && delivery.body) schedule(tenant, delivery, null)
}

const reasonOf = (error: unknown) => {
  const cause = (error as { cause?: { code?: string } })?.cause?.code ?? ''
  if ((error as Error)?.name === 'TimeoutError' || (error as Error)?.name === 'AbortError') return 'timeout'
  if (cause === 'ENOTFOUND' || cause === 'EAI_AGAIN') return 'dns'
  if (cause === 'ECONNREFUSED' || cause === 'ECONNRESET') return 'refused'
  if (cause.includes('CERT') || cause.includes('TLS') || cause.includes('SSL')) return 'tls'
  return 'failed'
}

/** One try: signs the body with the current secret, POSTs it and records the answer. */
export async function attempt(tenant: MockTenant, delivery: StoredDelivery, event: H3Event | null): Promise<StoredDelivery> {
  const store = integrationsOf(tenant)
  const webhook = store.webhooks.find(item => item.id === delivery.webhook_id)
  if (!webhook || !delivery.body) return delivery
  const timestamp = Math.floor(Date.now() / 1000)
  const signature = `sha256=${createHmac('sha256', webhook.secret).update(signedPayload(timestamp, delivery.body)).digest('hex')}`
  const headers = deliveryHeaders(delivery.event, delivery.id, timestamp, signature)
  const started = Date.now()
  let entry: WebhookAttempt
  try {
    const answer = await fetch(webhook.url, { method: 'POST', headers, body: delivery.body, redirect: 'manual', signal: AbortSignal.timeout(WEBHOOK_TIMEOUT_MS) })
    const text = (await answer.text()).slice(0, 2000)
    entry = { at: iso(started), status_code: answer.status, duration_ms: Date.now() - started, error: answer.ok ? null : `HTTP ${answer.status}` }
    delivery.response = { headers: Object.fromEntries([...answer.headers.entries()].filter(([name]) => ['content-type', 'content-length', 'server', 'date'].includes(name))), body: text || null }
  } catch (error) {
    entry = { at: iso(started), status_code: null, duration_ms: Date.now() - started, error: reasonOf(error) }
    delivery.response = null
  }
  delivery.history.push(entry)
  delivery.request_headers = { ...headers, 'X-Formalie-Signature': 'sha256=••••' }
  const ok = entry.status_code !== null && entry.status_code >= 200 && entry.status_code < 300
  if (ok) {
    delivery.status = 'delivered'
    delivery.next_retry_at = null
    if (!delivery.test) webhook.consecutive_failures = 0
  } else if (!delivery.test && delivery.history.length <= WEBHOOK_RETRY_MINUTES.length) {
    delivery.status = 'retrying'
    delivery.next_retry_at = iso(Date.now() + WEBHOOK_RETRY_MINUTES[delivery.history.length - 1]! * 60_000)
  } else {
    delivery.status = 'failed'
    delivery.next_retry_at = null
  }
  if (!ok && !delivery.test) {
    webhook.consecutive_failures += 1
    if (webhook.enabled && webhook.consecutive_failures >= WEBHOOK_AUTO_PAUSE) {
      webhook.enabled = false
      webhook.paused_reason = 'failures'
      if (event) recordAudit(event, tenant, { action: 'integrations.webhook_paused', actor: { type: 'system', id: null, name: 'Formalie', email: null }, resource: { type: 'webhook', id: webhook.id, name: webhook.name }, reason: `${WEBHOOK_AUTO_PAUSE} failed deliveries in a row` })
    }
  }
  saveIntegrations()
  if (delivery.status === 'retrying') schedule(tenant, delivery, event)
  return delivery
}

/** A new delivery for a webhook (the body built by the caller); the first try starts at once. */
export function queueDelivery(tenant: MockTenant, webhook: StoredWebhook, input: { event: WebhookEvent | 'ping'; test: boolean; form_id: string | null; response_id: string | null; body: Record<string, unknown>; personal: Set<string> }, event: H3Event | null) {
  const store = integrationsOf(tenant)
  const id = crypto.randomUUID()
  const body = JSON.stringify({ id: `evt_${encodeId(id)}`, ...input.body })
  const delivery: StoredDelivery = {
    id,
    webhook_id: webhook.id,
    event: input.event,
    test: input.test,
    form_id: input.form_id,
    response_id: input.response_id,
    at: new Date().toISOString(),
    status: 'retrying',
    next_retry_at: null,
    body,
    logged_body: JSON.stringify(maskAnswers(JSON.parse(body), input.personal)),
    request_headers: {},
    response: null,
    history: [],
  }
  store.deliveries.unshift(delivery)
  store.deliveries.splice(MAX_DELIVERIES)
  saveIntegrations()
  return { delivery, done: attempt(tenant, delivery, event) }
}

/**
 * A response event from anywhere in the mock (form page, API, portal): every switched-on webhook
 * that listens to this event and form gets a delivery. Never throws, never waits.
 */
export function emitResponseEvent(event: H3Event, tenant: MockTenant, type: WebhookEvent, input: { form: StoredForm; response: { id: string; submitted_at?: string; status?: string; channel?: string; answers?: Record<string, unknown> }; previous_status?: string }) {
  try {
    const hooks = integrationsOf(tenant).webhooks.filter(hook => hook.enabled && hook.events.includes(type) && (!hook.form_ids.length || hook.form_ids.includes(input.form.id)))
    if (!hooks.length) return
    const schema = schemaOf(input.form, null)
    const personal = new Set(schema ? allFields(schema).filter(field => PERSONAL_TYPES.has(field.type)).map(field => field.key) : [])
    const body = {
      type,
      created_at: new Date().toISOString(),
      test: false,
      data: {
        form: { id: encodeId(input.form.id), name: input.form.name },
        response: { id: encodeId(input.response.id), ...(input.response.submitted_at ? { submitted_at: input.response.submitted_at } : {}), ...(input.response.status ? { status: input.response.status } : {}), ...(input.response.channel ? { channel: input.response.channel } : {}), ...(input.response.answers ? { answers: input.response.answers } : {}) },
        ...(input.previous_status ? { previous_status: input.previous_status } : {}),
      },
    }
    for (const hook of hooks) void queueDelivery(tenant, hook, { event: type, test: false, form_id: input.form.id, response_id: input.response.id, body, personal }, event).done.catch(() => {})
  } catch (error) {
    console.error('[webhooks]', error)
  }
}

// Timers do not survive a restart: pick up retries that are still due
for (const tenant of MOCK_TENANTS) if (stores.has(tenant.id)) resumeRetries(tenant)

/** The same, looked up by response id: answers, status and channel as they are now (only ids for a deletion). */
export function emitResponse(event: H3Event, tenant: MockTenant, type: WebhookEvent, form: StoredForm, responseId: string, previousStatus?: string) {
  try {
    if (!integrationsOf(tenant).webhooks.some(hook => hook.enabled && hook.events.includes(type))) return
    if (type === 'response.deleted') return emitResponseEvent(event, tenant, type, { form, response: { id: responseId } })
    const found = findResponse(tenant, responseId)
    if (!found) return
    const { entry } = found
    emitResponseEvent(event, tenant, type, { form, response: { id: entry.id, submitted_at: new Date(entry.at).toISOString(), status: entry.status, channel: entry.channel, answers: answersOf(found.form, entry) }, previous_status: previousStatus })
  } catch (error) {
    console.error('[webhooks]', error)
  }
}

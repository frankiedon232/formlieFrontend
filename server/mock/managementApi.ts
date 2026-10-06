/**
 * Formalie's own management API in the mock (F13 M6, docs/API-CONTRACT.md → Management API): what an
 * organisation's code calls with an API key from API service → API keys. Plain HTTPS + JSON at
 * `https://api.formalie.dev/v1/…` (development: `https://localhost:2202/public-api/v1/…`).
 *
 *   GET    /v1/forms                       forms:read      (page, per_page, status)
 *   GET    /v1/forms/{id}                  forms:read      the form and its questions
 *   PATCH  /v1/forms/{id}                  forms:write     { status: "published" | "closed" }
 *   GET    /v1/forms/{id}/responses        responses:read  (page, per_page, status, since)
 *   GET    /v1/responses/{id}              responses:read
 *   PATCH  /v1/responses/{id}              responses:write { status?, tags? }
 *   DELETE /v1/responses/{id}              responses:write
 *   GET    /v1/webhooks                    webhooks:read
 *   GET    /v1/audit                       audit:read      (page, per_page)
 *
 * Ids are references (never real ids). Every call counts on the key (calls per day, last used and
 * from where) and changes are audited as the key (actor type `api_key`). 600 calls a minute per key.
 */
import type { H3Event } from 'h3'
import type { ApiKeyScope } from '#shared/types/integrations'
import { RESPONSE_STATUSES, type ResponseStatus } from '#shared/types/responses'
import { ERROR_CODES, type ErrorCode } from '#shared/utils/errors/codes'
import { allFields } from '#shared/utils/forms/build'
import { recordAudit, auditLogOf } from './core/audit'
import { decodeId, encodeId } from './core/ids'
import { formsOf, saveForms, type StoredForm } from './data/formStore'
import { emitResponse, hashKey, integrationsOf, keyStatusOf, saveIntegrations, toWebhook, type StoredManagementKey } from './data/integrationStore'
import { answersOf, findResponse, formResponses, type IndexedResponse } from './data/responseData'
import { updateReview } from './data/responseReview'
import { schemaOf } from './data/apiStore'
import { MOCK_TENANTS, type MockTenant } from './data/tenants'

class ManagementError extends Error {
  constructor(
    readonly code: ErrorCode,
    readonly details: { field: string; message: string }[] = [],
  ) {
    super(code)
  }
}
const windows = new Map<string, number[]>()
const LIMIT = 600

function send(event: H3Event, status: number, body: unknown) {
  setResponseStatus(event, status)
  setResponseHeader(event, 'content-type', 'application/json; charset=utf-8')
  setResponseHeader(event, 'cache-control', 'no-store')
  setResponseHeader(event, 'x-request-id', crypto.randomUUID())
  return body
}

/** The key in `Authorization: Bearer formalie_key_…`, its organisation, and the scope it needs. */
function callerKey(event: H3Event, scope: ApiKeyScope): { tenant: MockTenant; key: StoredManagementKey } {
  const secret = (getHeader(event, 'authorization') ?? '').replace(/^Bearer\s+/i, '').trim()
  if (!secret.startsWith('formalie_key_')) throw new ManagementError('FRM-API-1010')
  const hash = hashKey(secret)
  for (const tenant of MOCK_TENANTS) {
    const key = integrationsOf(tenant).keys.find(item => item.secret_hash === hash)
    if (!key) continue
    const status = keyStatusOf(key)
    if (status === 'revoked' || status === 'expired') throw new ManagementError('FRM-API-1010')
    const now = Date.now()
    const recent = (windows.get(key.id) ?? []).filter(at => at > now - 60_000)
    if (recent.length >= LIMIT) {
      const wait = Math.max(1, Math.ceil(((recent[0] ?? now) + 60_000 - now) / 1000))
      setResponseHeader(event, 'Retry-After', wait)
      throw new ManagementError('FRM-GEN-1029')
    }
    windows.set(key.id, [...recent, now])
    const day = new Date().toISOString().slice(0, 10)
    key.calls[day] = (key.calls[day] ?? 0) + 1
    key.last_used_at = new Date().toISOString()
    key.last_used_ip = (getHeader(event, 'x-forwarded-for')?.split(',')[0]?.trim() || getRequestIP(event) || null)?.replace(/^::ffff:/i, '') ?? null
    saveIntegrations()
    if (!key.scopes.includes(scope)) throw new ManagementError('FRM-API-1009', [{ field: 'scope', message: scope }])
    return { tenant, key }
  }
  throw new ManagementError('FRM-API-1010')
}

const actorOf = (key: StoredManagementKey) => ({ type: 'api_key' as const, id: key.id, name: `API key: ${key.name}`, email: null })
const pageOf = (event: H3Event) => {
  const query = getQuery(event)
  return { page: Math.max(1, Number(query.page) || 1), perPage: Math.min(100, Math.max(1, Number(query.per_page) || 20)) }
}
const paged = <T>(items: T[], page: number, perPage: number) => ({ data: items.slice((page - 1) * perPage, page * perPage), meta: { page, per_page: perPage, total: items.length, total_pages: Math.max(1, Math.ceil(items.length / perPage)) } })

const formView = (form: StoredForm) => ({ id: encodeId(form.id), name: form.name, status: form.status, responses_count: form.responses_count, created_at: form.created_at, updated_at: form.updated_at })
const responseView = (form: StoredForm, entry: IndexedResponse) => ({ id: encodeId(entry.id), form: { id: encodeId(form.id), name: form.name }, number: entry.number, submitted_at: new Date(entry.at).toISOString(), status: entry.status, tags: entry.tags, channel: entry.channel, language: entry.language, answers: answersOf(form, entry) })

function formById(tenant: MockTenant, ref: string | undefined) {
  const id = ref ? decodeId(ref) : null
  const form = id ? formsOf(tenant).forms.find(item => item.id === id && !item.deleted_at) : undefined
  if (!form) throw new ManagementError('FRM-GEN-1004')
  return form
}
function responseById(tenant: MockTenant, ref: string | undefined) {
  const id = ref ? decodeId(ref) : null
  const found = id ? findResponse(tenant, id) : null
  if (!found) throw new ManagementError('FRM-GEN-1004')
  return found
}
async function jsonBody(event: H3Event): Promise<Record<string, unknown>> {
  const raw = (await readRawBody(event, 'utf8')) ?? ''
  if (!raw) return {}
  try {
    const parsed = JSON.parse(raw) as unknown
    if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) throw new Error('object')
    return parsed as Record<string, unknown>
  } catch {
    throw new ManagementError('FRM-GEN-1001', [{ field: 'body', message: 'Send a JSON object.' }])
  }
}

async function route(event: H3Event, parts: string[]) {
  const method = event.method.toUpperCase()
  const [resource, ref, sub, extra] = parts
  if (extra !== undefined) throw new ManagementError('FRM-API-1006')

  if (resource === 'forms' && !ref) {
    if (method !== 'GET') throw new ManagementError('FRM-API-1008')
    const { tenant } = callerKey(event, 'forms:read')
    const { page, perPage } = pageOf(event)
    const status = getQuery(event).status
    const forms = formsOf(tenant).forms.filter(form => !form.deleted_at && (typeof status !== 'string' || form.status === status))
    return send(event, 200, paged(forms.map(formView), page, perPage))
  }
  if (resource === 'forms' && ref && !sub) {
    if (method === 'GET') {
      const { tenant } = callerKey(event, 'forms:read')
      const form = formById(tenant, ref)
      const schema = schemaOf(form, null)
      return send(event, 200, { data: { ...formView(form), questions: schema ? allFields(schema).map(field => ({ key: field.key, label: field.label, type: field.type, required: !!field.required })) : [] } })
    }
    if (method === 'PATCH') {
      const { tenant, key } = callerKey(event, 'forms:write')
      const form = formById(tenant, ref)
      const body = await jsonBody(event)
      if (body.status !== 'published' && body.status !== 'closed') throw new ManagementError('FRM-GEN-1002', [{ field: 'status', message: 'published or closed' }])
      if (!form.published_schema || !['published', 'closed'].includes(form.status)) throw new ManagementError('FRM-GEN-1002', [{ field: 'status', message: 'Publish the form in Formalie first.' }])
      if (form.status !== body.status) {
        const before = form.status
        form.status = body.status
        form.updated_at = new Date().toISOString()
        saveForms()
        recordAudit(event, tenant, { action: 'forms.updated', actor: actorOf(key), resource: { type: 'form', id: form.id, name: form.name }, changes: [{ field: 'status', before, after: form.status }] })
      }
      return send(event, 200, { data: formView(form) })
    }
    throw new ManagementError('FRM-API-1008')
  }
  if (resource === 'forms' && ref && sub === 'responses') {
    if (method !== 'GET') throw new ManagementError('FRM-API-1008')
    const { tenant } = callerKey(event, 'responses:read')
    const form = formById(tenant, ref)
    const { page, perPage } = pageOf(event)
    const query = getQuery(event)
    const since = typeof query.since === 'string' ? Date.parse(query.since) : NaN
    const list = formResponses(tenant, form).filter(entry => (typeof query.status !== 'string' || entry.status === query.status) && (Number.isNaN(since) || entry.at >= since))
    const slice = paged(list, page, perPage)
    return send(event, 200, { data: slice.data.map(entry => responseView(form, entry)), meta: slice.meta })
  }
  if (resource === 'responses' && ref && !sub) {
    if (method === 'GET') {
      const { tenant } = callerKey(event, 'responses:read')
      const { form, entry } = responseById(tenant, ref)
      return send(event, 200, { data: responseView(form, entry) })
    }
    if (method === 'PATCH') {
      const { tenant, key } = callerKey(event, 'responses:write')
      const { form, entry } = responseById(tenant, ref)
      const body = await jsonBody(event)
      const status = body.status as ResponseStatus | undefined
      if (status !== undefined && !RESPONSE_STATUSES.includes(status)) throw new ManagementError('FRM-GEN-1002', [{ field: 'status', message: RESPONSE_STATUSES.join(', ') }])
      const tags = body.tags
      if (tags !== undefined && (!Array.isArray(tags) || tags.some(tag => typeof tag !== 'string' || tag.length > 40) || tags.length > 20)) throw new ManagementError('FRM-GEN-1002', [{ field: 'tags', message: 'up to 20 texts' }])
      const by = { id: key.id, name: `API key: ${key.name}` }
      const changes = [...(status && status !== entry.status ? [{ field: 'status', before: entry.status, after: status }] : []), ...(tags ? [{ field: 'tags', before: entry.tags, after: [...new Set(tags as string[])] }] : [])]
      if (changes.length) {
        updateReview(form.id, entry.id, review => {
          if (status) review.status = status
          if (tags) review.tags = [...new Set(tags as string[])]
          review.history = [...changes.map(change => ({ id: crypto.randomUUID(), at: new Date().toISOString(), by, ...change })), ...(review.history ?? [])].slice(0, 200)
        })
        recordAudit(event, tenant, { action: 'responses.updated', actor: actorOf(key), resource: { type: 'response', id: entry.id, name: form.name }, changes: changes.map(change => ({ field: change.field, before: JSON.stringify(change.before), after: JSON.stringify(change.after) })) })
        if (status && status !== entry.status) emitResponse(event, tenant, 'response.status_changed', form, entry.id, entry.status)
      }
      const updated = findResponse(tenant, entry.id)!
      return send(event, 200, { data: responseView(updated.form, updated.entry) })
    }
    if (method === 'DELETE') {
      const { tenant, key } = callerKey(event, 'responses:write')
      const { form, entry } = responseById(tenant, ref)
      updateReview(form.id, entry.id, review => (review.deleted_at = new Date().toISOString()))
      recordAudit(event, tenant, { action: 'responses.deleted', actor: actorOf(key), resource: { type: 'response', id: entry.id, name: form.name } })
      emitResponse(event, tenant, 'response.deleted', form, entry.id)
      return send(event, 200, { data: { id: ref, deleted: true } })
    }
    throw new ManagementError('FRM-API-1008')
  }
  if (resource === 'webhooks' && !ref) {
    if (method !== 'GET') throw new ManagementError('FRM-API-1008')
    const { tenant } = callerKey(event, 'webhooks:read')
    return send(event, 200, { data: integrationsOf(tenant).webhooks.map(hook => toWebhook(tenant, hook)).map(({ id, name, url, events, forms, status, created_at }) => ({ id: encodeId(id), name, url, events, forms: forms.map(form => ({ id: encodeId(form.id), name: form.name })), status, created_at })) })
  }
  if (resource === 'audit' && !ref) {
    if (method !== 'GET') throw new ManagementError('FRM-API-1008')
    const { tenant } = callerKey(event, 'audit:read')
    const { page, perPage } = pageOf(event)
    const events = auditLogOf(tenant).map(item => ({ id: encodeId(item.id), occurred_at: item.occurred_at, action: item.action, outcome: item.outcome, actor: { type: item.actor.type, name: item.actor.name }, resource: item.resource ? { type: item.resource.type, name: item.resource.name } : null }))
    return send(event, 200, paged(events, page, perPage))
  }
  throw new ManagementError('FRM-API-1006')
}

/** `/v1/…` (path without the `/v1`). */
export async function handleManagementApi(event: H3Event, parts: string[]) {
  try {
    return await route(event, parts)
  } catch (error) {
    if (error instanceof ManagementError) {
      const definition = ERROR_CODES[error.code]
      return send(event, definition.status, { error: { code: error.code, message: definition.message, details: error.details } })
    }
    console.error('[management-api]', error)
    return send(event, 500, { error: { code: 'FRM-GEN-5000', message: ERROR_CODES['FRM-GEN-5000'].message, details: [] } })
  }
}

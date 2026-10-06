/**
 * The public API in the mock (F13, docs/API-CONTRACT.md → API service → Calling an endpoint): what
 * apps and Postman call. Plain HTTPS + JSON, no portal envelope (SECURITY-PROTOCOL §9).
 *
 *   POST   /{apiKey}/token                      client id + secret → short-lived access token
 *   GET    /{apiKey}/{endpoint}                 list (page, per_page, sort, filters)
 *   GET    /{apiKey}/{endpoint}/{recordId}      one
 *   POST   /{apiKey}/{endpoint}                 a new response (Idempotency-Key replays)
 *   PUT    /{apiKey}/{endpoint}/{recordId}      change accepted answers
 *   DELETE /{apiKey}/{endpoint}/{recordId}      remove (kept in the audit trail)
 *
 * Reachable in development at `https://localhost:2202/public-api/…` and, with a hosts entry, at
 * `https://api.formalie.dev:2202/…` (server/middleware/api-host.ts). Order of checks: address key →
 * endpoint → token → switched on → method → scope → required headers → signature → the form's rules.
 * Test tokens never touch real responses: writes are checked and answered, nothing is stored.
 */
import { createHmac, timingSafeEqual } from 'node:crypto'
import type { H3Event } from 'h3'
import { checkSubmission } from '#shared/utils/forms/submission'
import { allFields } from '#shared/utils/forms/build'
import { isFileField } from '#shared/utils/forms/file-answers'
import { validateAnswer } from '#shared/utils/forms/validate'
import { exampleRecord } from '#shared/utils/apiService/endpoints'
import { scopeAllows, tokenPrefix, tokenStatusOf } from '#shared/utils/apiService/tokens'
import { ERROR_CODES, type ErrorCode } from '#shared/utils/errors/codes'
import type { ApiMethod } from '#shared/utils/urls/public'
import { recordAudit } from './core/audit'
import { decodeId, encodeId } from './core/ids'
import { apiOf, hashSecret, saveApi, schemaOf, type StoredApiEndpoint, type StoredApiToken } from './data/apiStore'
import { formsOf, saveForms } from './data/formStore'
import { answersOf, formResponses, type IndexedResponse } from './data/responseData'
import { updateReview } from './data/responseReview'
import { responsesOf, saveResponses } from './data/responseStore'
import { MOCK_TENANTS, type MockTenant } from './data/tenants'

class PublicError extends Error {
  constructor(
    readonly code: ErrorCode,
    readonly details: { field: string; message: string }[] = [],
  ) {
    super(code)
  }
}
/** Short-lived access tokens from `/{apiKey}/token` (memory only, like a cache). */
const accessTokens = new Map<string, { tenant: string; token: string; expires: number }>()

function send(event: H3Event, status: number, body: unknown) {
  setResponseStatus(event, status)
  setResponseHeader(event, 'content-type', 'application/json; charset=utf-8')
  setResponseHeader(event, 'cache-control', 'no-store')
  setResponseHeader(event, 'x-request-id', crypto.randomUUID())
  return body
}
const fail = (event: H3Event, error: PublicError) => {
  const definition = ERROR_CODES[error.code]
  return send(event, definition.status, { error: { code: error.code, message: definition.message, details: error.details } })
}

function tenantByKey(key: string): MockTenant | null {
  for (const tenant of MOCK_TENANTS) {
    const api = apiOf(tenant)
    if (api.api_key === key) return tenant
    if (api.previous_key === key && api.previous_until && Date.parse(api.previous_until) > Date.now()) return tenant
  }
  return null
}
const same = (a: string, b: string) => a.length === b.length && timingSafeEqual(Buffer.from(a), Buffer.from(b))
const live = (token: StoredApiToken) => ['active', 'expiring'].includes(tokenStatusOf(token))
const matches = (token: StoredApiToken, secret: string) => {
  const hash = hashSecret(secret)
  return same(token.secret_hash, hash) || (!!token.previous_hash && !!token.rotating_until && Date.parse(token.rotating_until) > Date.now() && same(token.previous_hash, hash))
}

/** POST /{apiKey}/token: client credentials → a short-lived bearer token. */
function issueAccessToken(event: H3Event, tenant: MockTenant, body: Record<string, unknown>) {
  const token = apiOf(tenant).tokens.find(item => item.kind === 'client' && item.client_id === body.client_id)
  if (!token || typeof body.client_secret !== 'string' || !matches(token, body.client_secret) || !live(token)) throw new PublicError('FRM-API-1010')
  const access = `${tokenPrefix('access', token.mode)}${crypto.randomUUID().replace(/-/g, '')}`
  const seconds = (token.lifetime_minutes ?? 15) * 60
  accessTokens.set(access, { tenant: tenant.id, token: token.id, expires: Date.now() + seconds * 1000 })
  token.last_used_at = new Date().toISOString()
  saveApi()
  return send(event, 200, { access_token: access, token_type: 'Bearer', expires_in: seconds })
}

/** The token behind `Authorization: Bearer …` (a static token or a short-lived one). */
function callerToken(event: H3Event, tenant: MockTenant): StoredApiToken {
  const bearer = /^Bearer\s+(\S+)$/i.exec(getHeader(event, 'authorization') ?? '')?.[1]
  if (!bearer) throw new PublicError('FRM-API-1010')
  const tokens = apiOf(tenant).tokens
  const short = accessTokens.get(bearer)
  const token = short ? (short.tenant === tenant.id && short.expires > Date.now() ? tokens.find(item => item.id === short.token) : undefined) : tokens.find(item => item.kind === 'static' && matches(item, bearer))
  if (!token || !live(token)) throw new PublicError('FRM-API-1010')
  return token
}

/** HMAC-SHA256 of `{timestamp}.{METHOD}.{path}.{body}` with the signing secret, within 5 minutes. */
function checkSignature(event: H3Event, token: StoredApiToken, method: string, path: string, raw: string) {
  const timestamp = getHeader(event, 'x-formalie-timestamp') ?? ''
  const signature = (getHeader(event, 'x-formalie-signature') ?? '').replace(/^sha256=/, '')
  if (!/^\d{9,11}$/.test(timestamp) || Math.abs(Date.now() / 1000 - Number(timestamp)) > 300 || !token.signing_secret) throw new PublicError('FRM-API-1012')
  const expected = createHmac('sha256', token.signing_secret).update(`${timestamp}.${method}.${path}.${raw}`).digest('hex')
  if (!same(expected, signature)) throw new PublicError('FRM-API-1012')
}

/** A response as the API returns it: its reference, when, status and the returned answers (file ids as references too). */
function record(form: Parameters<typeof answersOf>[0], entry: IndexedResponse, endpoint: StoredApiEndpoint) {
  const data = answersOf(form, entry)
  const types = new Map(allFields(schemaOf(form, endpoint.version) ?? { schema_version: 1, pages: [] }).map(field => [field.key, field.type]))
  const value = (key: string) => {
    const answer = data[key] ?? null
    if (!isFileField(types.get(key) ?? '') || !Array.isArray(answer)) return answer
    return answer.map(file => (file && typeof file === 'object' && 'id' in file ? { ...(file as Record<string, unknown>), id: encodeId(String((file as { id: unknown }).id)) } : file))
  }
  return { id: encodeId(entry.id), submitted_at: new Date(entry.at).toISOString(), status: entry.status, data: Object.fromEntries(endpoint.fields.filter(field => field.returned).map(field => [field.key, value(field.key)])) }
}

export async function handlePublicApi(event: H3Event, path: string) {
  try {
    const [key = '', name = '', recordRef, extra] = path.replace(/^\/+|\/+$/g, '').split('/')
    const method = event.method.toUpperCase()
    const tenant = tenantByKey(key)
    if (!tenant || extra !== undefined) throw new PublicError('FRM-API-1006')
    const raw = ['POST', 'PUT'].includes(method) ? ((await readRawBody(event, 'utf8')) ?? '') : ''
    let body: Record<string, unknown> = {}
    if (raw) {
      try {
        const parsed = JSON.parse(raw) as unknown
        if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) throw new Error('object')
        body = parsed as Record<string, unknown>
      } catch {
        throw new PublicError('FRM-GEN-1001', [{ field: 'body', message: 'Send a JSON object.' }])
      }
    }
    if (name === 'token' && !recordRef) {
      if (method !== 'POST') throw new PublicError('FRM-API-1008')
      return issueAccessToken(event, tenant, body)
    }

    const api = apiOf(tenant)
    const endpoint = api.endpoints.find(item => item.name === name)
    if (!endpoint) throw new PublicError('FRM-API-1006')
    const token = callerToken(event, tenant)
    const service = api.services.find(item => item.id === endpoint.service_id)
    const form = formsOf(tenant).forms.find(item => item.id === endpoint.form_id && !item.deleted_at)
    const schema = form ? schemaOf(form, endpoint.version) : null
    if (endpoint.status !== 'active' || service?.status !== 'active' || !form || form.status !== 'published' || !schema) throw new PublicError('FRM-API-1007')
    const allowed: ApiMethod[] = endpoint.methods
    if (!(['GET', 'POST', 'PUT', 'DELETE'] as const).includes(method as ApiMethod) || !allowed.includes(method as ApiMethod) || (recordRef ? method === 'POST' : method === 'PUT' || method === 'DELETE')) throw new PublicError('FRM-API-1008')
    if (!scopeAllows(token.scopes, { endpoint_id: endpoint.id, service_id: endpoint.service_id, method: method as ApiMethod })) throw new PublicError('FRM-API-1009')
    const missing = (endpoint.headers ?? []).filter(header => (getHeader(event, header.name) ?? '') !== header.value)
    if (missing.length) throw new PublicError('FRM-API-1011', missing.map(header => ({ field: header.name, message: 'missing_or_wrong' })))
    if (token.signing) checkSignature(event, token, method, `/${key}/${name}${recordRef ? `/${recordRef}` : ''}`, raw)
    token.last_used_at = new Date().toISOString()
    saveApi()
    const test = token.mode === 'test'
    const actor = { type: 'api_key' as const, id: token.id, name: `API: ${token.name}`, email: null }
    const fields = new Map(allFields(schema).map(field => [field.key, field]))

    // Reading
    if (method === 'GET') {
      if (test) {
        const sample = exampleRecord(endpoint.fields.map(field => ({ ...field, label: fields.get(field.key)?.label ?? field.key, type: fields.get(field.key)?.type ?? 'short_text', page: 0, form_required: false, acceptable: true, filterable: false })))
        return send(event, 200, recordRef ? { data: { ...sample, id: recordRef }, meta: { test: true } } : { data: [sample], meta: { page: 1, per_page: 1, total: 1, test: true } })
      }
      const entries = formResponses(tenant, form)
      if (recordRef) {
        const id = decodeId(recordRef)
        const entry = id ? entries.find(item => item.id === id) : undefined
        if (!entry) throw new PublicError('FRM-API-1013')
        return send(event, 200, { data: record(form, entry, endpoint) })
      }
      const query = getQuery(event)
      const filters = endpoint.fields.filter(field => field.filter && typeof query[field.key] === 'string')
      let list = filters.length ? entries.filter(entry => { const data = answersOf(form, entry); return filters.every(field => { const value = data[field.key]; const wanted = String(query[field.key]); return Array.isArray(value) ? value.map(String).includes(wanted) : String(value ?? '') === wanted }) }) : entries
      list = [...list].sort((a, b) => (query.sort === 'submitted_at' ? a.at - b.at : b.at - a.at))
      const perPage = Math.min(endpoint.page_size, Math.max(1, Number(query.per_page) || Math.min(20, endpoint.page_size)))
      const page = Math.max(1, Number(query.page) || 1)
      return send(event, 200, { data: list.slice((page - 1) * perPage, page * perPage).map(entry => record(form, entry, endpoint)), meta: { page, per_page: perPage, total: list.length, total_pages: Math.max(1, Math.ceil(list.length / perPage)) } })
    }

    // Writing: only accepted questions, then the form's own rules
    const accepted = new Set(endpoint.fields.filter(field => field.accept).map(field => field.key))
    const refused = Object.keys(body).filter(item => !accepted.has(item))
    if (refused.length) throw new PublicError('FRM-API-1014', refused.map(item => ({ field: item, message: 'not_accepted' })))

    if (method === 'POST') {
      const required = endpoint.fields.filter(field => field.required && (body[field.key] == null || body[field.key] === ''))
      if (required.length) throw new PublicError('FRM-RESP-1001', required.map(field => ({ field: field.key, message: 'required' })))
      const { issues, answers } = checkSubmission(schema, body)
      if (issues.length) throw new PublicError('FRM-RESP-1001', issues.map(issue => ({ field: issue.key, message: issue.code })))
      const idempotency = getHeader(event, 'idempotency-key')?.slice(0, 100)
      const submissionId = idempotency ? `api:${endpoint.id}:${idempotency}` : `api:${crypto.randomUUID()}`
      const earlier = idempotency ? responsesOf(tenant).responses.find(item => item.submission_id === submissionId) : undefined
      if (earlier) {
        const entry = formResponses(tenant, form).find(item => item.id === earlier.id)
        if (entry) return send(event, 200, { data: record(form, entry, endpoint), meta: { replayed: true } })
      }
      if (test) return send(event, 201, { data: { id: encodeId(crypto.randomUUID()), submitted_at: new Date().toISOString(), status: 'new', data: Object.fromEntries(endpoint.fields.filter(field => field.returned).map(field => [field.key, answers[field.key] ?? null])) }, meta: { test: true } })
      const stored = { id: crypto.randomUUID(), form_id: form.id, form_version: endpoint.version ?? form.versions?.[0]?.number ?? null, submitted_at: new Date().toISOString(), language: schema.settings?.language ?? 'en', data: answers, submission_id: submissionId, channel: 'api' as const, meta: { ip: getRequestIP(event, { xForwardedFor: true }) ?? 'unknown', user_agent: (getHeader(event, 'user-agent') ?? '').slice(0, 300) } }
      responsesOf(tenant).responses.unshift(stored)
      saveResponses()
      form.responses_count += 1
      saveForms()
      recordAudit(event, tenant, { action: 'responses.submitted', actor, resource: { type: 'form', id: form.id, name: form.name }, changes: [{ field: 'channel', before: null, after: 'api' }], metadata: { endpoint: endpoint.name } })
      const entry = formResponses(tenant, form).find(item => item.id === stored.id)!
      return send(event, 201, { data: record(form, entry, endpoint) })
    }

    // PUT / DELETE on one record
    const id = recordRef ? decodeId(recordRef) : null
    const entry = id ? formResponses(tenant, form).find(item => item.id === id) : undefined
    if (!entry && !test) throw new PublicError('FRM-API-1013')
    if (method === 'DELETE') {
      if (!test) {
        updateReview(form.id, entry!.id, review => (review.deleted_at = new Date().toISOString()))
        recordAudit(event, tenant, { action: 'responses.deleted', actor, resource: { type: 'response', id: entry!.id, name: form.name }, metadata: { endpoint: endpoint.name } })
      }
      return send(event, 200, { data: { id: recordRef, deleted: true }, ...(test ? { meta: { test: true } } : {}) })
    }
    const problems = Object.entries(body).flatMap(([field, value]) => {
      const definition = fields.get(field)
      const issue = definition ? validateAnswer(definition, value, !!definition.required) : null
      return issue ? [{ field, message: issue.code }] : []
    })
    if (problems.length) throw new PublicError('FRM-RESP-1001', problems)
    if (test || !entry) return send(event, 200, { data: { id: recordRef, ...body }, meta: { test: true } })
    const before = answersOf(form, entry)
    updateReview(form.id, entry.id, review => {
      review.data = { ...review.data, ...body }
      review.history = [...Object.entries(body).map(([field, value]) => ({ id: crypto.randomUUID(), at: new Date().toISOString(), by: { id: token.id, name: actor.name }, field: `answer:${field}`, before: before[field] ?? null, after: value ?? null })), ...(review.history ?? [])].slice(0, 200)
    })
    recordAudit(event, tenant, { action: 'responses.updated', actor, resource: { type: 'response', id: entry.id, name: form.name }, changes: Object.keys(body).map(field => ({ field: fields.get(field)?.label ?? field, before: JSON.stringify(before[field] ?? null), after: JSON.stringify(body[field] ?? null) })), metadata: { endpoint: endpoint.name } })
    const updated = formResponses(tenant, form).find(item => item.id === entry.id)!
    return send(event, 200, { data: record(form, updated, endpoint) })
  } catch (error) {
    if (error instanceof PublicError) return fail(event, error)
    console.error('[public-api]', error)
    return fail(event, new PublicError('FRM-GEN-5000'))
  }
}

/** `/public-api/**` (development, mock only). */
export default defineEventHandler(event => handlePublicApi(event, event.path.split('?')[0]!.replace(/^\/public-api/, '')))

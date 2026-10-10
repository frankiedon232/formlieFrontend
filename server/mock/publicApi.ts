/**
 * The public API in the mock (F13, docs/API-CONTRACT.md → API service → Calling an endpoint): what
 * apps and Postman call. Plain HTTPS + JSON, no portal envelope (SECURITY-PROTOCOL §9).
 *
 *   POST   /{apiKey}/token                      client id + secret → short-lived access token
 *   GET    /{apiKey}/{endpoint}                 list (page, per_page, sort, filters)
 *   GET    /{apiKey}/{endpoint}/{recordId}      one
 *   POST   /{apiKey}/{endpoint}                 a new response (Formalie-Key replays)
 *   PUT    /{apiKey}/{endpoint}/{recordId}      change accepted answers
 *   DELETE /{apiKey}/{endpoint}/{recordId}      remove (kept in the audit trail)
 *   POST   /{apiKey}/{endpoint}/files?field=    one file (multipart/form-data, field "file") → its id for the JSON
 *
 * Reachable in development at `https://localhost:2202/public-api/…` and, with a hosts entry, at
 * `https://api.formalie.dev:2202/…` (server/middleware/api-host.ts). Order of checks: address key →
 * endpoint → access rules (IP, Origin domain, country) → rate limit per IP → token → rate limits per
 * token and endpoint → switched on → method → scope → required headers → signature → the form's rules.
 * Mock only: `X-Forwarded-For` sets the caller's IP, `X-Debug-Country` its country and `X-Debug-Network`
 * its anonymous networks (vpn, proxy, tor, hosting), so rules can
 * be tried from Postman (the real service takes the connection's address and GeoIP).
 * Test tokens never touch real responses: writes are checked and answered, nothing is stored.
 * Browsers: an Origin from the service's allowed websites gets CORS headers and its OPTIONS preflight a 204;
 * other websites' preflights → FRM-API-1015 (leftovers L6). HTTPS only is the real service's (TLS) job.
 */
import { responsesAllowed } from './core/plan'
import { notifyResponse } from './data/notificationStore'
import { emailResponse } from './data/responseEmails'
import { createHash, timingSafeEqual } from 'node:crypto'
import type { H3Event } from 'h3'
import { checkSubmission } from '#shared/utils/forms/submission'
import { choiceFilter, choiceOut, choicesIn } from '#shared/utils/apiService/choices'
import { libraryOf } from './data/libraryStore'
import { cascadeClosed, fitAnswer } from '#shared/utils/forms/cascade'
import { allFields, type FormField } from '#shared/utils/forms/build'
import { isFileField, maxFileBytes } from '#shared/utils/forms/file-answers'
import { acceptsFile, looksLikePicture, parseAccept, pictureAccept } from '#shared/utils/forms/file-types'
import type { FileAnswer } from '#shared/types/public'
import { attachRespondentFiles, respondentFile, storeApiFile } from './routes/uploads'
import { validateAnswer } from '#shared/utils/forms/validate'
import { endpointFieldsOf, exampleRecord } from '#shared/utils/apiService/endpoints'
import { canonicalJson, checkCallKey, scopeAllows, secretPreview, tokenPrefix, tokenStatusOf } from '#shared/utils/apiService/tokens'
import { decideAccess, rulesFor, type AccessCaller } from '#shared/utils/apiService/access'
import { normaliseOrigin, originAllowed } from '#shared/utils/apiService/origins'
import { ERROR_CODES, type ErrorCode } from '#shared/utils/errors/codes'
import type { ApiMethod } from '#shared/utils/urls/public'
import { recordAudit } from './core/audit'
import { decodeId, encodeId } from './core/ids'
import { apiOf, hashSecret, saveApi, schemaOf, type StoredApiEndpoint, type StoredApiToken } from './data/apiStore'
import { formsOf, saveForms } from './data/formStore'
import { answersOf, formResponses, type IndexedResponse } from './data/responseData'
import { updateReview, reviewOf } from './data/responseReview'
import { fingerprintOf, responsesOf, saveResponses } from './data/responseStore'
import { identityOf, maskEmail, matchIdentity } from '#shared/utils/forms/identity'
import { MOCK_TENANTS, type MockTenant } from './data/tenants'
import { recordLog } from './data/apiTraffic'
import { maskAnswers, PERSONAL_TYPES } from './core/mask'
import { API_NETWORKS } from '#shared/types/apiService'
import { channelsOf } from '#shared/types/forms'
import { emitResponse } from './data/integrationStore'

class PublicError extends Error {
  constructor(
    readonly code: ErrorCode,
    // Extra facts sit next to field and message as plain values (owner, 2026-10-06: clean answers, no JSON in a string)
    readonly details: ({ field: string; message: string } & Record<string, string | null>)[] = [],
    readonly headers: Record<string, string> = {},
  ) {
    super(code)
  }
}
/** Calls in the last minute per key (`ip:…`, `token:…`, `endpoint:…`), memory only. */
const windows = new Map<string, number[]>()
const today = () => new Date().toISOString().slice(0, 10)
/** Counts a call against a per-minute limit; over it → 429 with Retry-After. Returns what is left. */
function rateLimit(tenant: MockTenant, key: string, limit: number | null): { limit: number; remaining: number } | null {
  if (limit == null) return null
  const now = Date.now()
  const recent = (windows.get(key) ?? []).filter(at => at > now - 60_000)
  if (recent.length >= limit) {
    const api = apiOf(tenant)
    api.limited[today()] = (api.limited[today()] ?? 0) + 1
    const retry = Math.max(1, Math.ceil((recent[0]! + 60_000 - now) / 1000))
    throw new PublicError('FRM-GEN-1029', [{ field: key.split(':')[0]!, message: `limit ${limit} per minute` }], { 'Retry-After': String(retry), 'X-RateLimit-Limit': String(limit), 'X-RateLimit-Remaining': '0', 'X-RateLimit-Reset': String(Math.ceil((now + retry * 1000) / 1000)) })
  }
  recent.push(now)
  windows.set(key, recent)
  return { limit, remaining: limit - recent.length }
}
/** Who is calling: IP (mock: X-Forwarded-For first), the browser's Origin / Referer host, the country (mock: X-Debug-Country). */
function callerOf(event: H3Event): AccessCaller {
  const ip = (getHeader(event, 'x-forwarded-for')?.split(',')[0]?.trim() || getRequestIP(event) || '0.0.0.0').replace(/^::ffff:/i, '')
  let domain: string | null = null
  const origin = getHeader(event, 'origin') ?? getHeader(event, 'referer')
  if (origin) {
    try {
      domain = new URL(origin).hostname.toLowerCase()
    } catch {
      domain = null
    }
  }
  const country = getHeader(event, 'x-debug-country')?.trim().toUpperCase() || null
  // Mock only: X-Debug-Network (vpn, proxy, tor, hosting) stands in for the backend's IP intelligence
  const networks = (getHeader(event, 'x-debug-network') ?? '').split(',').map(item => item.trim().toLowerCase()).filter(item => (API_NETWORKS as readonly string[]).includes(item))
  return { ip, domain, country: country && /^[A-Z]{2}$/.test(country) ? country : null, networks }
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
  for (const [name, value] of Object.entries(error.headers)) setResponseHeader(event, name, value)
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
  const tokens = apiOf(tenant).tokens
  const token = tokens.find(item => item.kind === 'client' && item.client_id === body.client_id)
  // Two ways to sign in, never both (owner, 2026-10-06): a bearer token sent here says so
  const sent = [body.client_secret, body.client_id, /^Bearer\s+(\S+)$/i.exec(getHeader(event, 'authorization') ?? '')?.[1]].filter((value): value is string => typeof value === 'string' && !!value)
  if (!token && sent.some(value => tokens.some(item => item.kind === 'static' && matches(item, value)))) throw new PublicError('FRM-API-1010', [{ field: 'token', message: 'bearer_token: send it as Authorization: Bearer with each call, not to /token' }])
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
  const valid = short && short.tenant === tenant.id && short.expires > Date.now()
  const token = short ? (valid ? (short.token === CONSOLE ? consoleToken() : tokens.find(item => item.id === short.token)) : undefined) : tokens.find(item => item.kind === 'static' && matches(item, bearer))
  // A webhook token only identifies Formalie's calls to a webhook (owner, 2026-10-06)
  if (!token && tokens.some(item => item.kind === 'webhook' && matches(item, bearer))) throw new PublicError('FRM-API-1010', [{ field: 'Authorization', message: 'webhook_token: it only identifies Formalie\'s calls to your webhooks and can not call the API' }])
  // Two ways to sign in, never both (owner, 2026-10-06): a client id or secret sent as Bearer says so
  if (!token && tokens.some(item => item.kind === 'client' && (item.client_id === bearer || matches(item, bearer)))) throw new PublicError('FRM-API-1010', [{ field: 'Authorization', message: 'client_credentials: post the client id and secret to /token first, then send that short-lived token as Bearer' }])
  if (!token || !live(token)) throw new PublicError('FRM-API-1010')
  return token
}

/** The Docs console (F13 M5): a test token that may call everything, never stored, lives a minute. */
const CONSOLE = '__console__'
const consoleToken = (): StoredApiToken => ({ id: CONSOLE, name: 'Docs console', kind: 'static', mode: 'test', secret_hash: '', preview: '', previous_hash: null, rotating_until: null, client_id: null, lifetime_minutes: null, signing: false, signing_secret: null, scopes: { services: [], endpoints: [], methods: [] }, expires_at: null, last_used_at: null, created_by: { id: 'system', name: 'Formalie' }, created_at: new Date().toISOString(), revoked_at: null })
export function issueConsoleToken(tenantId: string) {
  const access = `${tokenPrefix('access', 'test')}${crypto.randomUUID().replace(/-/g, '')}`
  accessTokens.set(access, { tenant: tenantId, token: CONSOLE, expires: Date.now() + 60_000 })
  return access
}

/**
 * A response as the API returns it: its reference, when, status and the returned answers (file ids as
 * references too; choices as their option labels, owner 2026-10-08, with `defs` the form's questions).
 */
function record(form: Parameters<typeof answersOf>[0], entry: IndexedResponse, fields: { key: string; name: string; type: string; returned: boolean }[], defs?: Map<string, FormField>) {
  const data = answersOf(form, entry)
  const types = new Map(fields.map(field => [field.key, field.type]))
  const value = (key: string) => {
    const def = defs?.get(key)
    const answer = def ? choiceOut(def, data[key] ?? null) : (data[key] ?? null)
    if (!isFileField(types.get(key) ?? '') || !Array.isArray(answer)) return answer
    return answer.map(file => (file && typeof file === 'object' && 'id' in file ? { ...(file as Record<string, unknown>), id: encodeId(String((file as { id: unknown }).id)) } : file))
  }
  return { id: encodeId(entry.id), submitted_at: new Date(entry.at).toISOString(), status: entry.status, data: Object.fromEntries(fields.filter(field => field.returned).map(field => [field.name, value(field.key)])) }
}

/** What a call turned out to be, for the request log (filled in as the checks pass). */
interface CallContext {
  tenant?: MockTenant
  endpoint?: StoredApiEndpoint
  token?: StoredApiToken
  raw: string
  caller?: AccessCaller
  /** The call's Formalie-Key (Request logs show it). */
  callKey?: string
  /** Question key → API name, so error details name what the app sent. */
  names?: Map<string, string>
  /** Names the app sent that the endpoint does not know: reported exactly as sent. */
  unknown?: Set<string>
}
/** Answers whose question type holds personal data are masked in kept bodies. */
/** Handles a call and writes it to the request log (when the address key belongs to a workspace). */
export async function handlePublicApi(event: H3Event, path: string) {
  const context: CallContext = { raw: '' }
  const started = Date.now()
  const result = (await handle(event, path, context)) as { error?: { code?: string }; data?: unknown; meta?: Record<string, unknown> } | undefined
  // The token's expiry with every answer (owner, 2026-10-06: an expiry tracker in the data, never a surprise)
  if (context.token && context.token.id !== '__console__') {
    const expires = context.token.expires_at
    setResponseHeader(event, 'Formalie-Token-Expires', expires ?? 'never')
    if (result && 'data' in result) result.meta = { ...result.meta, token_expires_at: expires, token_expires_in_days: expires ? Math.max(0, Math.ceil((Date.parse(expires) - Date.now()) / 86_400_000)) : null }
  }
  const tenant = context.tenant
  // A browser's preflight is not a call: it stays out of the logs and the counts
  if (!tenant || event.method.toUpperCase() === 'OPTIONS') return result
  const api = apiOf(tenant)
  const endpoint = context.endpoint
  const schema = endpoint ? (() => { const form = formsOf(tenant).forms.find(item => item.id === endpoint.form_id); return form ? schemaOf(form, endpoint.version) : null })() : null
  const personal = new Set(schema ? allFields(schema).filter(field => PERSONAL_TYPES.has(field.type)).map(field => field.key) : [])
  const keep = api.logging?.keep_bodies ?? false
  let requestBody: unknown = null
  if (keep && context.raw) {
    try {
      requestBody = maskAnswers(JSON.parse(context.raw), personal)
    } catch {
      requestBody = context.raw.slice(0, 2000)
    }
  }
  const secretHeaders = new Set(['authorization', 'x-formalie-signature', 'cookie', ...(endpoint?.headers ?? []).map(header => header.name.toLowerCase())])
  const headers = Object.fromEntries(
    Object.entries(getRequestHeaders(event))
      .filter(([name, value]) => value !== undefined && name !== 'cookie' && name !== 'host' && !name.startsWith('sec-') && name !== 'connection')
      .map(([name, value]) => [name, name === 'authorization' ? `Bearer ${secretPreview(String(value).replace(/^Bearer\s+/i, ''))}` : secretHeaders.has(name) ? '••••' : String(value).slice(0, 200)]),
  )
  const service = endpoint ? api.services.find(item => item.id === endpoint.service_id) : undefined
  recordLog(tenant, { id: crypto.randomUUID(), at: new Date(started).toISOString(), method: event.method.toUpperCase(), path: path.split('?')[0]!, status: getResponseStatus(event), code: result?.error?.code ?? null, duration_ms: Date.now() - started, endpoint: endpoint ? { id: endpoint.id, name: endpoint.name } : null, service: service ? { id: service.id, name: service.name } : null, token: context.token ? { id: context.token.id, name: context.token.name, mode: context.token.mode } : null, ip: context.caller?.ip ?? getRequestIP(event) ?? '0.0.0.0', country: context.caller?.country ?? null, user_agent: (getHeader(event, 'user-agent') ?? '').slice(0, 200), request_id: context.callKey ?? String(getResponseHeader(event, 'x-request-id') ?? crypto.randomUUID()), request_body: requestBody, response_body: keep ? maskAnswers(result ?? null, personal) : null, request_headers: headers })
  return result
}

async function handle(event: H3Event, path: string, context: CallContext) {
  try {
    const [key = '', name = '', recordRef, extra] = path.replace(/^\/+|\/+$/g, '').split('/')
    const method = event.method.toUpperCase()
    const tenant = tenantByKey(key)
    context.tenant = tenant ?? undefined
    if (!tenant) throw new PublicError('FRM-API-1006', [{ field: 'address_key', message: 'unknown' }])
    if (extra !== undefined) throw new PublicError('FRM-API-1006', [{ field: 'path', message: 'too_long' }])
    // Browsers (leftovers L6): only the service's allowed websites get CORS answers; their preflights stop here.
    // Calls without an Origin (server apps, mobile apps, Postman) go on as before.
    const origin = getHeader(event, 'origin')
    if (origin) {
      const services = apiOf(tenant).services
      const target = name === 'token' ? null : (apiOf(tenant).endpoints.find(item => item.name === name) ?? null)
      const allowed = target ? services.find(item => item.id === target.service_id)?.allowed_origins : services.flatMap(item => item.allowed_origins ?? [])
      if (originAllowed(origin, allowed)) {
        setResponseHeaders(event, { 'Access-Control-Allow-Origin': normaliseOrigin(origin)!, Vary: 'Origin', 'Access-Control-Expose-Headers': 'Formalie-Token-Expires, Retry-After, X-RateLimit-Limit, X-RateLimit-Remaining, X-RateLimit-Reset' })
        if (method === 'OPTIONS') {
          setResponseHeaders(event, {
            'Access-Control-Allow-Methods': target ? [...target.methods, 'OPTIONS'].join(', ') : 'POST, OPTIONS',
            'Access-Control-Allow-Headers': ['Authorization', 'Content-Type', 'Formalie-Key', 'X-Formalie-Signature', ...(target?.headers ?? []).map(header => header.name)].join(', '),
            'Access-Control-Max-Age': '600',
          })
          setResponseStatus(event, 204)
          return null
        }
      } else if (method === 'OPTIONS') throw new PublicError('FRM-API-1015', [{ field: 'origin', message: 'not an allowed website' }])
    }
    // A file upload carries multipart/form-data, every other write a JSON object
    const upload = recordRef === 'files' && method === 'POST'
    const raw = ['POST', 'PUT'].includes(method) && !upload ? ((await readRawBody(event, 'utf8')) ?? '') : ''
    context.raw = raw.slice(0, 20_000)
    let body: Record<string, unknown> = {}
    // Bodies: 1 MB at most, and said to be JSON (owner, 2026-10-06: a clear answer for every mistake)
    if (Buffer.byteLength(raw) > 1_000_000) throw new PublicError('FRM-API-1018', [{ field: 'body', message: '1 MB' }])
    // Content-Type is JSON whatever is sent (owner, 2026-10-06: JSON by default, no argument)
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
      // The token address: only rules for everything apply, and the per-IP limit
      const caller = callerOf(event)
      const decision = decideAccess(apiOf(tenant).rules.filter(rule => rule.scope.type === 'all'), caller)
      if (!decision.allowed) throw new PublicError('FRM-API-1015', [{ field: decision.reason!, message: decision.rule?.value ?? 'no allow rule matched' }])
      rateLimit(tenant, `ip:${tenant.id}:${caller.ip}`, apiOf(tenant).limits.per_ip)
      return issueAccessToken(event, tenant, body)
    }

    const api = apiOf(tenant)
    const endpoint = api.endpoints.find(item => item.name === name)
    if (!endpoint) throw new PublicError('FRM-API-1006', [{ field: 'endpoint', message: 'unknown' }])
    context.endpoint = endpoint
    // Access rules: a block refuses; when allow rules apply, one must match
    const caller = callerOf(event)
    context.caller = caller
    const applies = rulesFor(api.rules, endpoint)
    const decision = decideAccess(applies, caller)
    const decided = decision.rule ? api.rules.find(item => item.id === decision.rule!.id) : undefined
    if (decided) {
      decided.hits[today()] = (decided.hits[today()] ?? 0) + 1
      decided.last_hit_at = new Date().toISOString()
      saveApi()
    }
    if (!decision.allowed) throw new PublicError('FRM-API-1015', [{ field: decision.reason!, message: decision.rule?.value ?? 'no allow rule matched' }])
    rateLimit(tenant, `ip:${tenant.id}:${caller.ip}`, api.limits.per_ip)
    const token = callerToken(event, tenant)
    context.token = token
    const left = rateLimit(tenant, `token:${token.id}`, api.limits.per_token)
    rateLimit(tenant, `endpoint:${endpoint.id}`, api.limits.per_endpoint)
    if (left) {
      setResponseHeader(event, 'X-RateLimit-Limit', String(left.limit))
      setResponseHeader(event, 'X-RateLimit-Remaining', String(left.remaining))
    }
    const service = api.services.find(item => item.id === endpoint.service_id)
    const form = formsOf(tenant).forms.find(item => item.id === endpoint.form_id && !item.deleted_at)
    const schema = form ? schemaOf(form, endpoint.version) : null
    if (service?.status !== 'active') throw new PublicError('FRM-API-1007', [{ field: 'service', message: 'switched_off' }])
    if (!form || form.status !== 'published' || !schema) throw new PublicError('FRM-API-1007', [{ field: 'form', message: 'not_published' }])
    if (!channelsOf(form).includes('api')) throw new PublicError('FRM-API-1007', [{ field: 'form', message: 'not_for_api' }])
    // Not live yet: only test tokens get through, so it can be tried before going live (owner, 2026-10-06)
    if (endpoint.status !== 'active' && token.mode !== 'test') throw new PublicError('FRM-API-1007', [{ field: 'endpoint', message: 'not_live' }])
    // The choices as the portal shows them: worked out from the form (a question the form requires is always accepted)
    const choices = endpointFieldsOf(schema, endpoint.fields)
    // API names ↔ question keys (owner, 2026-10-06): apps send and get the names, the form keeps its keys
    const keyOf = new Map(choices.map(field => [field.name, field.key]))
    context.names = new Map(choices.map(field => [field.key, field.name]))
    // Names this endpoint does not know are refused with the other not-accepted ones (below)
    const unknownNames = Object.keys(body).filter(name => !keyOf.has(name))
    context.unknown = new Set(unknownNames)
    body = Object.fromEntries(Object.entries(body).filter(([name]) => keyOf.has(name)).map(([name, value]) => [keyOf.get(name)!, value]))
    const allowed: ApiMethod[] = endpoint.methods
    if (!(['GET', 'POST', 'PUT', 'DELETE'] as const).includes(method as ApiMethod) || !allowed.includes(method as ApiMethod) || (recordRef && !upload ? method === 'POST' : method === 'PUT' || method === 'DELETE')) throw new PublicError('FRM-API-1008')
    if (!scopeAllows(token.scopes, { endpoint_id: endpoint.id, service_id: endpoint.service_id, method: method as ApiMethod })) {
      // Say which part of the token's scope refused it (owner, 2026-10-06), never what else it may call
      const { services, endpoints, methods } = token.scopes
      const part = methods.length && !methods.includes(method as ApiMethod) ? { field: 'method', message: 'not_allowed_for_token' } : endpoints.length && !endpoints.includes(endpoint.id) ? { field: 'endpoint', message: 'not_allowed_for_token' } : { field: 'service', message: services.some(id => !apiOf(tenant).services.some(item => item.id === id)) ? 'token_service_deleted' : 'not_allowed_for_token' }
      throw new PublicError('FRM-API-1009', [part])
    }
    // The headers (owner, 2026-10-06): Authorization (checked above), Content-Type (JSON by default) and the
    // Formalie-Key, a new unique id: required on POST (a retry with the same key and body answers with its first
    // record), optional on GET, PUT and DELETE (checked when sent; Request logs find a call by it). No other headers.
    const callKey = getHeader(event, 'formalie-key')?.trim() ?? ''
    if (method === 'POST' || callKey) {
      const problem = checkCallKey(callKey)
      if (problem) throw new PublicError('FRM-API-1011', [{ field: 'Formalie-Key', message: problem }])
    }
    context.callKey = callKey || undefined
    token.last_used_at = new Date().toISOString()
    saveApi()
    const test = token.mode === 'test'
    const actor = { type: 'api_key' as const, id: token.id, name: `API: ${token.name}`, email: null }
    const fields = new Map(allFields(schema).map(field => [field.key, field]))
    // Choices may be sent by label as records show them (owner 2026-10-08): labels become option values
    body = choicesIn(allFields(schema), body)
    // Labels for records: the form's options, plus options of its lists the form no longer offers (retired
    // since), so older answers still read as what was chosen
    const lists = new Map(libraryOf(tenant).lists.map(list => [list.id, list]))
    const labelDefs = new Map([...fields].map(([key, field]) => {
      const list = field.option_set_id ? lists.get(field.option_set_id) : undefined
      const known = new Set((field.options ?? []).map(option => option.value))
      const older = list ? list.options.filter(option => !known.has(option.value)).map(option => ({ value: option.value, label: option.label })) : []
      return [key, older.length ? { ...field, options: [...(field.options ?? []), ...older] } : field]
    }))

    // Files: checked like the form page, stored at once (test tokens: checked only) → an id for the JSON
    if (upload) {
      const asked = String(getQuery(event).field ?? '')
      const key = keyOf.get(asked) ?? ''
      const definition = fields.get(key)
      if (!definition || !isFileField(definition.type) || !choices.some(item => item.key === key && item.accept)) throw new PublicError('FRM-API-1014', [{ field: asked || 'field', message: 'not_accepted' }])
      const file = (await readMultipartFormData(event))?.find(part => part.name === 'file' && part.filename)
      if (!file) throw new PublicError('FRM-GEN-1001', [{ field: 'file', message: 'Send the file as multipart/form-data in a field named file.' }])
      const props = (definition.props ?? {}) as Record<string, unknown>
      const image = definition.type === 'image_upload'
      const accept = image ? pictureAccept(String(props.accept ?? '')) : String(props.accept ?? '')
      const described = { name: file.filename!.slice(0, 200), type: file.type ?? 'application/octet-stream' }
      if (!acceptsFile(accept, described) || (image && !looksLikePicture(described))) throw new PublicError('FRM-RESP-1001', [{ field: key, message: 'file_type' }])
      const stored = storeApiFile({ tenantId: tenant.id, formId: form.id, field: key, name: described.name, contentType: described.type, size: file.data.length, maxBytes: maxFileBytes(props), kind: image ? 'image' : 'file', listed: parseAccept(accept).filter(type => type.startsWith('.')), bytes: new Uint8Array(file.data), check: test })
      if (stored === 'size' || stored === 'type') throw new PublicError('FRM-RESP-1001', [{ field: key, message: stored === 'size' ? 'file_size' : 'file_type' }])
      return send(event, 201, { data: { ...stored, id: encodeId(test ? crypto.randomUUID() : stored.id) }, ...(test ? { meta: { test: true } } : {}) })
    }

    // Reading
    if (method === 'GET') {
      if (test) {
        const sample = exampleRecord(choices.map(field => ({ ...field, label: fields.get(field.key)?.label ?? field.key, type: fields.get(field.key)?.type ?? 'short_text', page: 0, form_required: false, acceptable: true, filterable: false })))
        return send(event, 200, recordRef ? { data: { ...sample, id: recordRef }, meta: { test: true } } : { data: [sample], meta: { page: 1, per_page: 1, total: 1, test: true } })
      }
      const entries = formResponses(tenant, form)
      if (recordRef) {
        const id = decodeId(recordRef)
        const entry = id ? entries.find(item => item.id === id) : undefined
        if (!entry) throw new PublicError('FRM-API-1013')
        return send(event, 200, { data: record(form, entry, choices, labelDefs) })
      }
      const query = getQuery(event)
      const filters = choices.filter(field => field.filter && typeof query[field.name] === 'string')
      let list = filters.length ? entries.filter(entry => { const data = answersOf(form, entry); return filters.every(field => { const value = data[field.key]; const def = fields.get(field.key); const wanted = def ? choiceFilter(def, String(query[field.name])) : String(query[field.name]); return Array.isArray(value) ? value.map(String).includes(wanted) : String(value ?? '') === wanted }) }) : entries
      list = [...list].sort((a, b) => (query.sort === 'submitted_at' ? a.at - b.at : b.at - a.at))
      const perPage = Math.min(endpoint.page_size, Math.max(1, Number(query.per_page) || Math.min(20, endpoint.page_size)))
      const page = Math.max(1, Number(query.page) || 1)
      return send(event, 200, { data: list.slice((page - 1) * perPage, page * perPage).map(entry => record(form, entry, choices, labelDefs)), meta: { page, per_page: perPage, total: list.length, total_pages: Math.max(1, Math.ceil(list.length / perPage)) } })
    }

    // Writing: only accepted questions, then the form's own rules
    const accepted = new Set(choices.filter(field => field.accept).map(field => field.key))
    const refused = [...unknownNames, ...Object.keys(body).filter(item => !accepted.has(item))]
    if (refused.length) throw new PublicError('FRM-API-1014', refused.map(item => ({ field: item, message: 'not_accepted' })))
    // File answers: ids from …/files (or { id }) → the stored files of this form and question, not used by another response
    const fileIds: string[] = []
    for (const [key, value] of Object.entries(body)) {
      const definition = fields.get(key)
      if (!definition || !isFileField(definition.type) || value == null) continue
      const refs = (Array.isArray(value) ? value : [value]).map(item => (typeof item === 'string' ? item : item && typeof item === 'object' && 'id' in item ? String((item as { id: unknown }).id) : ''))
      const files = refs.map(ref => {
        const id = decodeId(ref)
        if (test) return id || ref ? ({ id: id ?? ref, name: 'file', size: 0, type: 'application/octet-stream' } satisfies FileAnswer) : null
        return id ? respondentFile(id, form.id, key) : null
      })
      if (files.some(item => !item)) throw new PublicError('FRM-RESP-1001', [{ field: key, message: 'file' }])
      body[key] = files
      fileIds.push(...files.map(item => item!.id))
    }

    if (method === 'POST') {
      // A level of a list with levels with nothing under the choice above is not asked, so not required (F15 M2)
      const byId = new Map(allFields(schema).map(field => [field.id, field]))
      const closed = (key: string) => { const field = fields.get(key); return !!field && cascadeClosed(field, byId, body) }
      const required = choices.filter(field => field.required && (body[field.key] == null || body[field.key] === '') && !closed(field.key))
      if (required.length) throw new PublicError('FRM-RESP-1001', required.map(field => ({ field: field.key, message: 'required' })))
      const { issues, answers } = checkSubmission(schema, body)
      if (issues.length) throw new PublicError('FRM-RESP-1001', issues.map(issue => ({ field: issue.key, message: issue.code })))
      // The form's own response limit, or the plan's responses on each form (Subscription, F24)
      if (!test && ((form.response_limit != null && form.responses_count >= form.response_limit) || !responsesAllowed(tenant, form.responses_count))) throw new PublicError('FRM-FORM-1003')
      // A retry within 24 hours: the same key and body answer with the first record; the same key with another
      // body is refused, so a key reused by mistake never swallows a new record silently (owner, 2026-10-06)
      const store = apiOf(tenant)
      const since = Date.now() - 86_400_000
      store.replays = (store.replays ?? []).filter(item => Date.parse(item.at) > since)
      const replayKey = `${endpoint.id}:${context.callKey}`
      const hash = createHash('sha256').update(canonicalJson(body)).digest('hex')
      const earlier = store.replays.find(item => item.key === replayKey)
      if (earlier) {
        if (earlier.hash !== hash) throw new PublicError('FRM-API-1020', [{ field: 'Formalie-Key', message: 'used_for_another_body' }])
        if (earlier.answer) return send(event, 200, { ...(earlier.answer as object), meta: { replayed: true } })
        const entry = earlier.response_id ? formResponses(tenant, form).find(item => item.id === earlier.response_id) : undefined
        if (entry) return send(event, 200, { data: record(form, entry, choices, labelDefs), meta: { replayed: true } })
      }
      // The form's own duplicate rules, exactly as on its web page (owner, 2026-10-06: a new Formalie-Key is no
      // way round them): the same answers twice are refused; with the form's identity email, the same email is
      // refused and one a typo away is saved but flagged "possible duplicate" for review (an app can not confirm).
      const earlierResponses = responsesOf(tenant).responses.filter(item => item.form_id === form.id && !reviewOf(item.id)?.deleted_at) // deleted ones no longer count
      const fingerprint = fingerprintOf(answers)
      if (earlierResponses.some(item => item.fingerprint === fingerprint)) throw new PublicError('FRM-RESP-1005', [{ field: 'body', message: 'same_answers' }])
      let possibleDuplicate: { of: string; reason: string } | undefined
      const identity = identityOf(schema)
      if (identity.email) {
        const match = matchIdentity(schema, answers, earlierResponses, identity)
        if (match.level === 'clear') throw new PublicError('FRM-RESP-1006', [{ field: identity.email, message: 'already_submitted', submitted_at: match.record?.submitted_at ?? null, email: maskEmail(match.record?.data[identity.email]) || null }])
        if (match.level === 'likely') possibleDuplicate = { of: match.record!.id, reason: match.reason! }
      }
      const submissionId = `api:${endpoint.id}:${crypto.randomUUID()}`
      if (test) {
        const answer = { data: { id: encodeId(crypto.randomUUID()), submitted_at: new Date().toISOString(), status: 'new', data: Object.fromEntries(choices.filter(field => field.returned).map(field => [field.name, answers[field.key] ?? null])) }, meta: { test: true } }
        store.replays.unshift({ key: replayKey, hash, at: new Date().toISOString(), response_id: null, answer })
        saveApi()
        return send(event, 201, answer)
      }
      const stored = { id: crypto.randomUUID(), form_id: form.id, form_version: endpoint.version ?? form.versions?.[0]?.number ?? null, submitted_at: new Date().toISOString(), language: schema.settings?.language ?? 'en', data: answers, submission_id: submissionId, channel: 'api' as const, meta: { ip: getRequestIP(event, { xForwardedFor: true }) ?? 'unknown', user_agent: (getHeader(event, 'user-agent') ?? '').slice(0, 300) }, fingerprint, ...(possibleDuplicate ? { possible_duplicate: possibleDuplicate } : {}) }
      responsesOf(tenant).responses.unshift(stored)
      saveResponses()
      store.replays.unshift({ key: replayKey, hash, at: stored.submitted_at, response_id: stored.id })
      store.replays.splice(5000)
      saveApi()
      attachRespondentFiles(fileIds, stored.id)
      form.responses_count += 1
      saveForms()
      recordAudit(event, tenant, { action: 'responses.submitted', actor, resource: { type: 'form', id: form.id, name: form.name }, changes: [{ field: 'channel', before: null, after: 'api' }], metadata: { endpoint: endpoint.name } })
      emitResponse(event, tenant, 'response.created', form, stored.id)
      notifyResponse(event, tenant, form, stored.id, !!stored.possible_duplicate)
      emailResponse(event, tenant, form, schema, stored)
      const entry = formResponses(tenant, form).find(item => item.id === stored.id)!
      return send(event, 201, { data: record(form, entry, choices, labelDefs) })
    }

    // PUT / DELETE on one record
    const id = recordRef ? decodeId(recordRef) : null
    const entry = id ? formResponses(tenant, form).find(item => item.id === id) : undefined
    if (!entry && !test) throw new PublicError('FRM-API-1013')
    if (method === 'DELETE') {
      if (!test) {
        updateReview(form.id, entry!.id, review => (review.deleted_at = new Date().toISOString()))
        recordAudit(event, tenant, { action: 'responses.deleted', actor, resource: { type: 'response', id: entry!.id, name: form.name }, metadata: { endpoint: endpoint.name } })
        emitResponse(event, tenant, 'response.deleted', form, entry!.id)
      }
      return send(event, 200, { data: { id: recordRef, deleted: true }, ...(test ? { meta: { test: true } } : {}) })
    }
    const problems = Object.entries(body).flatMap(([field, value]) => {
      const definition = fields.get(field)
      const issue = definition ? validateAnswer(definition, value, !!definition.required) : null
      return issue ? [{ field, message: issue.code }] : []
    })
    // Lists with levels (F15 M2): a level sent must sit under the record's choice above (after this change);
    // levels below a changed one that no longer fit are cleared, as in the form
    const before = entry ? answersOf(form, entry) : {}
    const byId = new Map(allFields(schema).map(field => [field.id, field]))
    const merged: Record<string, unknown> = { ...before, ...body }
    for (const field of byId.values()) {
      if (!field.option_parent || merged[field.key] == null) continue
      const fitted = fitAnswer(field, byId, merged)
      if (JSON.stringify(fitted ?? null) === JSON.stringify(merged[field.key])) continue
      if (field.key in body) problems.push({ field: field.key, message: 'choice' })
      else body[field.key] = fitted ?? null
      merged[field.key] = fitted ?? null
    }
    if (problems.length) throw new PublicError('FRM-RESP-1001', problems)
    if (test || !entry) return send(event, 200, { data: { id: recordRef, ...body }, meta: { test: true } })
    attachRespondentFiles(fileIds, entry.id)
    updateReview(form.id, entry.id, review => {
      review.data = { ...review.data, ...body }
      review.history = [...Object.entries(body).map(([field, value]) => ({ id: crypto.randomUUID(), at: new Date().toISOString(), by: { id: token.id, name: actor.name }, field: `answer:${field}`, before: before[field] ?? null, after: value ?? null })), ...(review.history ?? [])].slice(0, 200)
    })
    recordAudit(event, tenant, { action: 'responses.updated', actor, resource: { type: 'response', id: entry.id, name: form.name }, changes: Object.keys(body).map(field => ({ field: fields.get(field)?.label ?? field, before: JSON.stringify(before[field] ?? null), after: JSON.stringify(body[field] ?? null) })), metadata: { endpoint: endpoint.name } })
    emitResponse(event, tenant, 'response.updated', form, entry.id)
    const updated = formResponses(tenant, form).find(item => item.id === entry.id)!
    return send(event, 200, { data: record(form, updated, choices, labelDefs) })
  } catch (error) {
    if (error instanceof PublicError) {
      // Details name what the app sent: the API name, not the question key
      const names = context.names
      return fail(event, names ? Object.assign(new PublicError(error.code, error.details.map(detail => ({ ...detail, field: context.unknown?.has(detail.field) ? detail.field : (names.get(detail.field) ?? detail.field) })), error.headers)) : error)
    }
    console.error('[public-api]', error)
    return fail(event, new PublicError('FRM-GEN-5000'))
  }
}

/** `/public-api/**` (development, mock only). */
export default defineEventHandler(event => handlePublicApi(event, event.path.split('?')[0]!.replace(/^\/public-api/, '')))

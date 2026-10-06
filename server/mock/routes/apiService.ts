/**
 * Mock API service management (F13 M1, docs/API-CONTRACT.md → API service). Admins only until F22.
 *
 *   GET    /api-service/settings          the organisation's address handle and base address
 *   GET    /api-services                  list (q, sort, filter[status])        · /insights
 *   GET    /api-services/:id              one                                  · POST · PATCH · DELETE
 *   POST   /api-services/:id/duplicate    a copy with copies of its endpoints (switched off)
 *   GET    /api-endpoints                 list (q, sort, filter[service|method|status]) · /insights
 *   GET    /api-endpoints/:id             one with its fields                  · POST · PATCH · DELETE
 *   POST   /api-service/key/rotate        a new address handle; the old one works for a grace period
 *   GET    /api-tokens                    list (q, sort, filter[status|mode|kind]) · /insights · /:id
 *   POST   /api-tokens                    a token; its secrets come back once     · PATCH · DELETE (revoked / expired)
 *   POST   /api-tokens/:id/rotate         new secrets (shown once); the old ones work for a grace period
 *   POST   /api-tokens/:id/revoke         stops it at once
 *
 * Endpoint names are unique in the organisation (FRM-API-1001); an endpoint needs a published
 * form (FRM-API-1002). The form's own rules decide which questions can be sent: required
 * questions are always accepted on POST, read-only ones, files and calculated values never.
 */
import { z } from 'zod'
import type { ApiInsights, ApiServiceSettings, ApiSetupSummary, ApiTokenSecrets, ApiTokenCreated, ApiTokenInsights, ApiUsage } from '#shared/types/apiService'
import { API_STATUSES, API_TOKEN_MODES, API_TOKEN_STATUSES } from '#shared/types/apiService'
import { checkHeaderName, checkHeaderValue, MAX_REQUIRED_HEADERS, ROTATION_GRACE_HOURS, secretPreview, TOKEN_LIFETIMES } from '#shared/utils/apiService/tokens'
import { checkEndpointName, endpointFieldsOf, API_PAGE_SIZE_MAX } from '#shared/utils/apiService/endpoints'
import { API_METHODS, type ApiMethod } from '#shared/utils/urls/public'
import { actorOf, recordAudit } from '../core/audit'
import { requireAdmin } from '../core/auth'
import { confirmPassword } from '../core/confirm'
import { MockError, ok, paginate, filtersOf } from '../core/respond'
import { defineMockRoute } from '../core/route'
import { parseBody } from '../core/validate'
import { API_BASE_URL, apiOf, endpointUsage, hashSecret, newSecret, saveApi, schemaOf, sumUsage, toEndpoint, toEndpointDetail, toService, toToken, type StoredApiEndpoint, type StoredApiToken } from '../data/apiStore'
import { formsOf } from '../data/formStore'
import { channelsOf } from '#shared/types/forms'
import type { MockTenant } from '../data/tenants'

const serviceInput = z.object({
  name: z.string().trim().min(1).max(80),
  description: z.string().trim().max(300).nullish(),
  status: z.enum(API_STATUSES).optional(),
})
const endpointInput = z.object({
  name: z.string().trim().max(64),
  description: z.string().trim().max(300).nullish(),
  service_id: z.string(),
  form_id: z.string(),
  version: z.number().int().positive().nullable(),
  methods: z.array(z.enum(API_METHODS)).max(4),
  fields: z.array(z.object({ key: z.string().max(64), accept: z.boolean(), required: z.boolean(), returned: z.boolean(), filter: z.boolean() })).max(500),
  page_size: z.number().int().min(1).max(API_PAGE_SIZE_MAX),
  headers: z.array(z.object({ name: z.string().trim().max(64), value: z.string().max(200).nullable() })).max(MAX_REQUIRED_HEADERS).optional(),
  status: z.enum(API_STATUSES).optional(),
})

const now = () => new Date().toISOString()
const sortRows = <T extends Record<string, unknown>>(rows: T[], sort: string) => {
  const desc = sort.startsWith('-')
  const key = desc ? sort.slice(1) : sort
  return rows.sort((a, b) => {
    const x = a[key] ?? ''
    const y = b[key] ?? ''
    const order = typeof x === 'number' && typeof y === 'number' ? x - y : String(x).localeCompare(String(y), undefined, { numeric: true })
    return desc ? -order : order
  })
}
const listOf = (value: unknown) => (typeof value === 'string' && value ? value.split(',') : [])
function insightsOf(usage: ApiUsage, statuses: ('active' | 'disabled')[], methods: ApiMethod[][]): ApiInsights {
  return {
    total: statuses.length,
    by_status: { active: statuses.filter(s => s === 'active').length, disabled: statuses.filter(s => s === 'disabled').length },
    by_method: Object.fromEntries(API_METHODS.map(method => [method, methods.filter(list => list.includes(method)).length])) as Record<ApiMethod, number>,
    calls_30d: usage.calls_30d,
    previous_30d: usage.previous_30d,
    errors_30d: usage.errors_30d,
    daily: usage.daily,
    avg_ms: usage.avg_ms,
  }
}

// ── Settings ─────────────────────────────────────────────────────────────────────────────

function settingsOf(tenant: MockTenant): ApiServiceSettings {
  const api = apiOf(tenant)
  const graceLeft = api.previous_until && Date.parse(api.previous_until) > Date.now()
  return { api_key: api.api_key, base_url: API_BASE_URL, previous_key: graceLeft ? (api.previous_key ?? null) : null, previous_until: graceLeft ? (api.previous_until ?? null) : null, rotated_at: api.rotated_at ?? null }
}

export const apiSettings = defineMockRoute(({ event }) => {
  const { tenant } = requireAdmin(event)
  return ok(settingsOf(tenant))
})

/** A new address handle; every endpoint's address changes, the old handle keeps answering for `grace_hours`. */
export const rotateApiKey = defineMockRoute(({ event, body }) => {
  const { tenant, user } = requireAdmin(event)
  const { grace_hours } = parseBody(z.object({ grace_hours: z.number().int().refine(n => ROTATION_GRACE_HOURS.includes(n)) }), body)
  const api = apiOf(tenant)
  const chars = 'ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnpqrstuvwxyz23456789'
  api.previous_key = grace_hours ? api.api_key : null
  api.previous_until = grace_hours ? new Date(Date.now() + grace_hours * 3_600_000).toISOString() : null
  api.api_key = Array.from(crypto.getRandomValues(new Uint8Array(10)), byte => chars[byte % chars.length]).join('')
  api.rotated_at = now()
  saveApi()
  recordAudit(event, tenant, { action: 'api.key_rotated', actor: actorOf(user), resource: { type: 'api_service', id: null, name: api.api_key }, metadata: { grace_hours: String(grace_hours) } })
  return ok(settingsOf(tenant))
})

// ── Services ─────────────────────────────────────────────────────────────────────────────

function findService(tenant: MockTenant, id: string | undefined) {
  const service = apiOf(tenant).services.find(item => item.id === id)
  if (!service) throw new MockError('FRM-GEN-1004')
  return service
}

export const listApiServices = defineMockRoute(({ event, query }) => {
  const { tenant } = requireAdmin(event)
  const filter = filtersOf(query)
  let rows = apiOf(tenant).services.map(item => toService(tenant, item))
  if (filter.status) rows = rows.filter(row => listOf(filter.status).includes(row.status))
  sortRows(rows as unknown as Record<string, unknown>[], typeof query.sort === 'string' && query.sort ? query.sort : 'name')
  const { data, meta } = paginate(rows, { ...query, sort: undefined }, (row, q) => `${row.name} ${row.description ?? ''}`.toLowerCase().includes(q))
  return ok(data, meta)
})

export const apiServiceInsights = defineMockRoute(({ event }) => {
  const { tenant } = requireAdmin(event)
  const api = apiOf(tenant)
  const services = api.services.map(item => toService(tenant, item))
  return ok(insightsOf(sumUsage(services), services.map(item => item.status), services.map(item => item.methods)))
})

export const getApiService = defineMockRoute(({ event }) => {
  const { tenant } = requireAdmin(event)
  return ok(toService(tenant, findService(tenant, getRouterParam(event, 'id'))))
})

export const createApiService = defineMockRoute(({ event, body }) => {
  const { tenant, user } = requireAdmin(event)
  const values = parseBody(serviceInput, body)
  const api = apiOf(tenant)
  if (api.services.some(item => item.name.toLowerCase() === values.name.toLowerCase())) throw new MockError('FRM-API-1003')
  const service = { id: crypto.randomUUID(), name: values.name, description: values.description || null, status: values.status ?? ('active' as const), created_by: { id: user.id, name: `${user.first_name} ${user.last_name}` }, created_at: now(), updated_at: now() }
  api.services.push(service)
  saveApi()
  recordAudit(event, tenant, { action: 'api.service_created', actor: actorOf(user), resource: { type: 'api_service', id: service.id, name: service.name } })
  return ok(toService(tenant, service), {}, 201)
})

export const updateApiService = defineMockRoute(({ event, body }) => {
  const { tenant, user } = requireAdmin(event)
  const service = findService(tenant, getRouterParam(event, 'id'))
  const values = parseBody(serviceInput.partial(), body)
  const api = apiOf(tenant)
  if (values.name && api.services.some(item => item.id !== service.id && item.name.toLowerCase() === values.name!.toLowerCase())) throw new MockError('FRM-API-1003')
  const before = { name: service.name, status: service.status }
  if (values.name !== undefined) service.name = values.name
  if (values.description !== undefined) service.description = values.description || null
  if (values.status !== undefined) service.status = values.status
  service.updated_at = now()
  saveApi()
  const resource = { type: 'api_service', id: service.id, name: service.name }
  if (values.status !== undefined && values.status !== before.status) recordAudit(event, tenant, { action: values.status === 'active' ? 'api.service_enabled' : 'api.service_disabled', actor: actorOf(user), resource })
  if ((values.name !== undefined && values.name !== before.name) || values.description !== undefined)
    recordAudit(event, tenant, { action: 'api.service_updated', actor: actorOf(user), resource, changes: values.name !== before.name && values.name !== undefined ? [{ field: 'name', before: before.name, after: service.name }] : [] })
  return ok(toService(tenant, service))
})

/** A free endpoint name: `name-copy`, `name-copy-2`, … */
function freeName(api: ReturnType<typeof apiOf>, base: string) {
  const stem = `${base}-copy`.slice(0, 58)
  for (let n = 1; ; n++) {
    const name = n === 1 ? stem : `${stem}-${n}`
    if (!api.endpoints.some(item => item.name === name)) return name
  }
}

export const duplicateApiService = defineMockRoute(({ event }) => {
  const { tenant, user } = requireAdmin(event)
  const source = findService(tenant, getRouterParam(event, 'id'))
  const api = apiOf(tenant)
  let name = `${source.name} (copy)`
  for (let n = 2; api.services.some(item => item.name.toLowerCase() === name.toLowerCase()); n++) name = `${source.name} (copy ${n})`
  const copy = { ...source, id: crypto.randomUUID(), name: name.slice(0, 80), status: 'disabled' as const, created_by: { id: user.id, name: `${user.first_name} ${user.last_name}` }, created_at: now(), updated_at: now() }
  api.services.push(copy)
  for (const endpoint of api.endpoints.filter(item => item.service_id === source.id))
    api.endpoints.push({ ...endpoint, id: crypto.randomUUID(), service_id: copy.id, name: freeName(api, endpoint.name), status: 'disabled', fields: endpoint.fields.map(field => ({ ...field })), headers: (endpoint.headers ?? []).map(header => ({ ...header })), methods: [...endpoint.methods], created_at: now(), updated_at: now() })
  saveApi()
  recordAudit(event, tenant, { action: 'api.service_created', actor: actorOf(user), resource: { type: 'api_service', id: copy.id, name: copy.name }, metadata: { copy_of: source.name } })
  return ok(toService(tenant, copy), {}, 201)
})

export const deleteApiService = defineMockRoute(({ event }) => {
  const { tenant, user } = requireAdmin(event)
  const service = findService(tenant, getRouterParam(event, 'id'))
  const api = apiOf(tenant)
  const removed = api.endpoints.filter(item => item.service_id === service.id).length
  api.services.splice(api.services.indexOf(service), 1)
  const gone = new Set(api.endpoints.filter(item => item.service_id === service.id).map(item => item.id))
  api.endpoints = api.endpoints.filter(item => item.service_id !== service.id)
  // Rules made for it (or its endpoints) go too
  api.rules = api.rules.filter(rule => !(rule.scope.type === 'service' && rule.scope.id === service.id) && !(rule.scope.type === 'endpoint' && gone.has(rule.scope.id ?? '')))
  saveApi()
  recordAudit(event, tenant, { action: 'api.service_deleted', actor: actorOf(user), resource: { type: 'api_service', id: service.id, name: service.name }, metadata: { endpoints: String(removed) } })
  return ok({ deleted: true, endpoints: removed })
})

// ── Endpoints ────────────────────────────────────────────────────────────────────────────

function findEndpoint(tenant: MockTenant, id: string | undefined) {
  const endpoint = apiOf(tenant).endpoints.find(item => item.id === id)
  if (!endpoint) throw new MockError('FRM-GEN-1004')
  return endpoint
}

export const listApiEndpoints = defineMockRoute(({ event, query }) => {
  const { tenant } = requireAdmin(event)
  const filter = filtersOf(query)
  let rows = apiOf(tenant).endpoints.map(item => toEndpoint(tenant, item))
  if (filter.service) rows = rows.filter(row => listOf(filter.service).includes(row.service.id))
  if (filter.form) rows = rows.filter(row => listOf(filter.form).includes(row.form.id))
  if (filter.status) rows = rows.filter(row => listOf(filter.status).includes(row.status))
  if (filter.method) rows = rows.filter(row => listOf(filter.method).some(method => row.methods.includes(method as ApiMethod)))
  const sort = typeof query.sort === 'string' && query.sort ? query.sort : 'name'
  sortRows(rows as unknown as Record<string, unknown>[], sort)
  const { data, meta } = paginate(rows, { ...query, sort: undefined }, (row, q) => `${row.name} ${row.form.name} ${row.service.name} ${row.description ?? ''}`.toLowerCase().includes(q))
  return ok(data, meta)
})

export const apiEndpointInsights = defineMockRoute(({ event, query }) => {
  const { tenant } = requireAdmin(event)
  const filter = filtersOf(query)
  let endpoints = apiOf(tenant).endpoints
  if (filter.service) endpoints = endpoints.filter(item => listOf(filter.service).includes(item.service_id))
  return ok(insightsOf(sumUsage(endpoints.map(item => endpointUsage(tenant, item))), endpoints.map(item => item.status), endpoints.map(item => item.methods)))
})

export const getApiEndpoint = defineMockRoute(({ event }) => {
  const { tenant } = requireAdmin(event)
  return ok(toEndpointDetail(tenant, findEndpoint(tenant, getRouterParam(event, 'id'))))
})

/** Checks an endpoint as the real service would, and keeps only what the form allows. */
function checked(tenant: MockTenant, values: z.infer<typeof endpointInput>, exceptId?: string): Omit<StoredApiEndpoint, 'id' | 'created_at' | 'updated_at'> {
  const api = apiOf(tenant)
  const problem = checkEndpointName(values.name)
  if (problem) throw new MockError('FRM-GEN-1002', [{ field: 'name', message: problem }])
  if (api.endpoints.some(item => item.id !== exceptId && item.name === values.name)) throw new MockError('FRM-API-1001', [{ field: 'name', message: 'taken' }])
  if (!api.services.some(item => item.id === values.service_id)) throw new MockError('FRM-GEN-1002', [{ field: 'service_id', message: 'required' }])
  const form = formsOf(tenant).forms.find(item => item.id === values.form_id && !item.deleted_at)
  if (!form) throw new MockError('FRM-GEN-1002', [{ field: 'form_id', message: 'required' }])
  const schema = schemaOf(form, values.version)
  if (!schema || form.status !== 'published') throw new MockError('FRM-API-1002', [{ field: 'form_id', message: 'not_published' }])
  if (!channelsOf(form).includes('api')) throw new MockError('FRM-API-1019', [{ field: 'form_id', message: 'not_for_api' }])
  if (!values.methods.length) throw new MockError('FRM-GEN-1002', [{ field: 'methods', message: 'required' }])
  const fields = endpointFieldsOf(schema, values.fields)
  const writes = values.methods.some(method => method === 'POST' || method === 'PUT')
  if (writes && !fields.some(field => field.accept)) throw new MockError('FRM-GEN-1002', [{ field: 'fields', message: 'accept' }])
  if (values.methods.includes('GET') && !fields.some(field => field.returned)) throw new MockError('FRM-GEN-1002', [{ field: 'fields', message: 'returned' }])
  // Required headers: valid, distinct names; a null value keeps the saved one
  const saved = api.endpoints.find(item => item.id === exceptId)?.headers ?? []
  const headers = (values.headers ?? saved.map(header => ({ name: header.name, value: null }))).map((header, index) => {
    const nameProblem = checkHeaderName(header.name)
    if (nameProblem) throw new MockError('FRM-GEN-1002', [{ field: `headers.${index}.name`, message: nameProblem }])
    const value = header.value ?? saved.find(item => item.name.toLowerCase() === header.name.toLowerCase())?.value ?? ''
    const valueProblem = checkHeaderValue(value)
    if (valueProblem) throw new MockError('FRM-GEN-1002', [{ field: `headers.${index}.value`, message: valueProblem }])
    return { name: header.name, value }
  })
  if (new Set(headers.map(header => header.name.toLowerCase())).size !== headers.length) throw new MockError('FRM-GEN-1002', [{ field: 'headers', message: 'duplicate' }])
  return {
    headers,
    service_id: values.service_id,
    name: values.name,
    description: values.description || null,
    form_id: form.id,
    version: values.version,
    methods: API_METHODS.filter(method => values.methods.includes(method)),
    fields: fields.map(({ key, accept, required, returned, filter }) => ({ key, accept, required, returned, filter })),
    page_size: values.page_size,
    // New endpoints start not live: test tokens can try them, live calls wait for Go live (owner, 2026-10-06)
    status: values.status ?? 'disabled',
  }
}

export const createApiEndpoint = defineMockRoute(({ event, body }) => {
  const { tenant, user } = requireAdmin(event)
  const values = parseBody(endpointInput, body)
  const endpoint: StoredApiEndpoint = { id: crypto.randomUUID(), ...checked(tenant, values), created_at: now(), updated_at: now() }
  apiOf(tenant).endpoints.push(endpoint)
  saveApi()
  recordAudit(event, tenant, { action: 'api.endpoint_created', actor: actorOf(user), resource: { type: 'api_endpoint', id: endpoint.id, name: endpoint.name }, metadata: { methods: endpoint.methods.join(', '), form: formsOf(tenant).forms.find(item => item.id === endpoint.form_id)?.name ?? '' } })
  return ok(toEndpointDetail(tenant, endpoint), {}, 201)
})

export const updateApiEndpoint = defineMockRoute(({ event, body }) => {
  const { tenant, user } = requireAdmin(event)
  const endpoint = findEndpoint(tenant, getRouterParam(event, 'id'))
  const resource = () => ({ type: 'api_endpoint', id: endpoint.id, name: endpoint.name })
  // Switching on / off alone
  const onlyStatus = z.object({ status: z.enum(API_STATUSES) }).strict().safeParse(body)
  if (onlyStatus.success) {
    if (onlyStatus.data.status !== endpoint.status) {
      endpoint.status = onlyStatus.data.status
      endpoint.updated_at = now()
      saveApi()
      recordAudit(event, tenant, { action: endpoint.status === 'active' ? 'api.endpoint_enabled' : 'api.endpoint_disabled', actor: actorOf(user), resource: resource() })
    }
    return ok(toEndpointDetail(tenant, endpoint))
  }
  const values = parseBody(endpointInput, body)
  const before = endpoint.name
  Object.assign(endpoint, checked(tenant, { ...values, status: values.status ?? endpoint.status }, endpoint.id), { updated_at: now() })
  saveApi()
  recordAudit(event, tenant, { action: 'api.endpoint_updated', actor: actorOf(user), resource: resource(), changes: before !== endpoint.name ? [{ field: 'name', before, after: endpoint.name }] : [], metadata: { methods: endpoint.methods.join(', ') } })
  return ok(toEndpointDetail(tenant, endpoint))
})

export const deleteApiEndpoint = defineMockRoute(({ event }) => {
  const { tenant, user } = requireAdmin(event)
  const endpoint = findEndpoint(tenant, getRouterParam(event, 'id'))
  const api = apiOf(tenant)
  api.endpoints.splice(api.endpoints.indexOf(endpoint), 1)
  api.rules = api.rules.filter(rule => !(rule.scope.type === 'endpoint' && rule.scope.id === endpoint.id))
  saveApi()
  recordAudit(event, tenant, { action: 'api.endpoint_deleted', actor: actorOf(user), resource: { type: 'api_endpoint', id: endpoint.id, name: endpoint.name } })
  return ok({ deleted: true })
})

/** GET /api-endpoints/form-fields?form_id&version: a form's questions as endpoint fields (the wizard, before saving). */
export const apiEndpointFormFields = defineMockRoute(({ event, query }) => {
  const { tenant } = requireAdmin(event)
  const form = formsOf(tenant).forms.find(item => item.id === query.form_id && !item.deleted_at)
  if (!form) throw new MockError('FRM-GEN-1004')
  const version = query.version ? Number(query.version) : null
  const schema = schemaOf(form, version)
  if (!schema || form.status !== 'published') throw new MockError('FRM-API-1002')
  return ok({ fields: endpointFieldsOf(schema), versions: (form.versions ?? []).map(item => item.number).sort((a, b) => b - a) })
})

// ── Tokens (M2) ──────────────────────────────────────────────────────────────────────────

const tokenInput = z.object({
  name: z.string().trim().min(1).max(80),
  kind: z.enum(['static', 'client']),
  mode: z.enum(API_TOKEN_MODES),
  scopes: z.object({ services: z.array(z.string()).max(100), endpoints: z.array(z.string()).max(500), methods: z.array(z.enum(API_METHODS)).max(4) }),
  expires_at: z.string().datetime().nullable(),
  lifetime_minutes: z.number().int().refine(n => TOKEN_LIFETIMES.includes(n)).nullish(),
  signing: z.boolean().optional(),
})

function findToken(tenant: MockTenant, id: string | undefined) {
  const token = apiOf(tenant).tokens.find(item => item.id === id)
  if (!token) throw new MockError('FRM-GEN-1004')
  return token
}
/** Scopes name services and endpoints of this organisation; an expiry is in the future and within 2 years. */
function checkToken(tenant: MockTenant, values: Pick<z.infer<typeof tokenInput>, 'scopes' | 'expires_at'>) {
  const api = apiOf(tenant)
  if (values.scopes.services.some(id => !api.services.some(item => item.id === id))) throw new MockError('FRM-GEN-1002', [{ field: 'scopes', message: 'services' }])
  if (values.scopes.endpoints.some(id => !api.endpoints.some(item => item.id === id))) throw new MockError('FRM-GEN-1002', [{ field: 'scopes', message: 'endpoints' }])
  if (values.expires_at) {
    const at = Date.parse(values.expires_at)
    if (at <= Date.now() || at > Date.now() + 731 * 86_400_000) throw new MockError('FRM-GEN-1002', [{ field: 'expires_at', message: 'range' }])
  }
}
/** New secrets for a token: the bearer token or client secret, and a signing secret when signing is on. */
function issue(token: StoredApiToken) {
  const secret = newSecret(token.kind, token.mode)
  const signing = token.signing ? newSecret('signing', token.mode) : null
  token.secret_hash = hashSecret(secret)
  token.secret = secret
  token.preview = secretPreview(secret)
  token.signing_secret = signing
  return { ...(token.kind === 'static' ? { token: secret } : { client_secret: secret }), ...(signing ? { signing_secret: signing } : {}) }
}

export const listApiTokens = defineMockRoute(({ event, query }) => {
  const { tenant } = requireAdmin(event)
  const filter = filtersOf(query)
  let rows = apiOf(tenant).tokens.map(item => toToken(tenant, item))
  if (filter.status) rows = rows.filter(row => listOf(filter.status).includes(row.status))
  if (filter.mode) rows = rows.filter(row => listOf(filter.mode).includes(row.mode))
  if (filter.kind) rows = rows.filter(row => listOf(filter.kind).includes(row.kind))
  sortRows(rows as unknown as Record<string, unknown>[], typeof query.sort === 'string' && query.sort ? query.sort : '-created_at')
  const { data, meta } = paginate(rows, { ...query, sort: undefined }, (row, q) => `${row.name} ${row.preview}`.toLowerCase().includes(q))
  return ok(data, meta)
})

export const apiTokenInsights = defineMockRoute(({ event }) => {
  const { tenant } = requireAdmin(event)
  const tokens = apiOf(tenant).tokens.map(item => toToken(tenant, item))
  const usage = sumUsage(tokens)
  const insights: ApiTokenInsights = {
    total: tokens.length,
    by_status: Object.fromEntries(API_TOKEN_STATUSES.map(status => [status, tokens.filter(item => item.status === status).length])) as ApiTokenInsights['by_status'],
    by_mode: { live: tokens.filter(item => item.mode === 'live').length, test: tokens.filter(item => item.mode === 'test').length },
    calls_30d: usage.calls_30d,
    previous_30d: usage.previous_30d,
    daily: usage.daily,
    unused_90d: tokens.filter(item => (item.status === 'active' || item.status === 'expiring') && Date.parse(item.last_used_at ?? item.created_at) < Date.now() - 90 * 86_400_000).length,
  }
  return ok(insights)
})

export const getApiToken = defineMockRoute(({ event }) => {
  const { tenant } = requireAdmin(event)
  return ok(toToken(tenant, findToken(tenant, getRouterParam(event, 'id'))))
})

export const createApiToken = defineMockRoute(({ event, body }) => {
  const { tenant, user } = requireAdmin(event)
  const values = parseBody(tokenInput, body)
  checkToken(tenant, values)
  const token: StoredApiToken = {
    id: crypto.randomUUID(),
    name: values.name,
    kind: values.kind,
    mode: values.mode,
    secret_hash: '',
    preview: '',
    previous_hash: null,
    rotating_until: null,
    client_id: values.kind === 'client' ? newSecret('client_id', values.mode) : null,
    lifetime_minutes: values.kind === 'client' ? (values.lifetime_minutes ?? 15) : null,
    signing: !!values.signing,
    signing_secret: null,
    scopes: values.scopes,
    expires_at: values.expires_at,
    last_used_at: null,
    created_by: { id: user.id, name: `${user.first_name} ${user.last_name}` },
    created_at: now(),
    revoked_at: null,
  }
  const secrets = issue(token)
  apiOf(tenant).tokens.unshift(token)
  saveApi()
  recordAudit(event, tenant, { action: 'api.token_created', actor: actorOf(user), resource: { type: 'api_token', id: token.id, name: token.name }, metadata: { kind: token.kind, mode: token.mode, preview: token.kind === 'client' ? token.client_id! : token.preview } })
  const created: ApiTokenCreated = { token: toToken(tenant, token), secrets }
  return ok(created, {}, 201)
})

export const updateApiToken = defineMockRoute(({ event, body }) => {
  const { tenant, user } = requireAdmin(event)
  const token = findToken(tenant, getRouterParam(event, 'id'))
  if (token.revoked_at) throw new MockError('FRM-API-1004')
  const values = parseBody(tokenInput.pick({ name: true, scopes: true, expires_at: true, lifetime_minutes: true }).partial(), body)
  checkToken(tenant, { scopes: values.scopes ?? token.scopes, expires_at: values.expires_at === undefined ? null : values.expires_at })
  const before = token.name
  if (values.name !== undefined) token.name = values.name
  if (values.scopes !== undefined) token.scopes = values.scopes
  if (values.expires_at !== undefined) token.expires_at = values.expires_at
  if (values.lifetime_minutes != null && token.kind === 'client') token.lifetime_minutes = values.lifetime_minutes
  saveApi()
  recordAudit(event, tenant, { action: 'api.token_updated', actor: actorOf(user), resource: { type: 'api_token', id: token.id, name: token.name }, changes: before !== token.name ? [{ field: 'name', before, after: token.name }] : [] })
  return ok(toToken(tenant, token))
})

export const rotateApiToken = defineMockRoute(({ event, body }) => {
  const { tenant, user } = requireAdmin(event)
  const token = findToken(tenant, getRouterParam(event, 'id'))
  if (token.revoked_at) throw new MockError('FRM-API-1004')
  const { grace_hours } = parseBody(z.object({ grace_hours: z.number().int().refine(n => ROTATION_GRACE_HOURS.includes(n)) }), body)
  token.previous_hash = grace_hours ? token.secret_hash : null
  token.rotating_until = grace_hours ? new Date(Date.now() + grace_hours * 3_600_000).toISOString() : null
  const secrets = issue(token)
  saveApi()
  recordAudit(event, tenant, { action: 'api.token_rotated', actor: actorOf(user), resource: { type: 'api_token', id: token.id, name: token.name }, metadata: { grace_hours: String(grace_hours) } })
  const created: ApiTokenCreated = { token: toToken(tenant, token), secrets }
  return ok(created)
})

export const revokeApiToken = defineMockRoute(({ event }) => {
  const { tenant, user } = requireAdmin(event)
  const token = findToken(tenant, getRouterParam(event, 'id'))
  if (!token.revoked_at) {
    token.revoked_at = now()
    token.previous_hash = null
    token.rotating_until = null
    saveApi()
    recordAudit(event, tenant, { action: 'api.token_revoked', actor: actorOf(user), resource: { type: 'api_token', id: token.id, name: token.name } })
  }
  return ok(toToken(tenant, token))
})

export const deleteApiToken = defineMockRoute(({ event }) => {
  const { tenant, user } = requireAdmin(event)
  const token = findToken(tenant, getRouterParam(event, 'id'))
  const view = toToken(tenant, token)
  if (view.status !== 'revoked' && view.status !== 'expired') throw new MockError('FRM-API-1005')
  const list = apiOf(tenant).tokens
  list.splice(list.indexOf(token), 1)
  saveApi()
  recordAudit(event, tenant, { action: 'api.token_deleted', actor: actorOf(user), resource: { type: 'api_token', id: token.id, name: token.name } })
  return ok({ deleted: true })
})

/** GET /api-service/setup: how far the organisation is (guided setup, owner 2026-10-06). */
export const apiSetup = defineMockRoute(({ event }) => {
  const { tenant } = requireAdmin(event)
  const api = apiOf(tenant)
  const tokens = api.tokens.filter(token => !token.revoked_at && (!token.expires_at || Date.parse(token.expires_at) > Date.now()))
  const setup: ApiSetupSummary = {
    services: api.services.length,
    endpoints: api.endpoints.length,
    endpoints_live: api.endpoints.filter(item => item.status === 'active').length,
    tokens_live: tokens.filter(token => token.mode === 'live').length,
    tokens_test: tokens.filter(token => token.mode === 'test').length,
    rules: api.rules.filter(rule => rule.enabled).length,
  }
  return ok(setup)
})

/** POST /api-tokens/:id/reveal { password }: the token's secrets again, after the password (owner, 2026-10-06). */
export const revealApiToken = defineMockRoute(({ event, body }) => {
  const { tenant, user } = requireAdmin(event)
  const token = apiOf(tenant).tokens.find(item => item.id === getRouterParam(event, 'id'))
  if (!token) throw new MockError('FRM-GEN-1004')
  if (token.revoked_at) throw new MockError('FRM-API-1004')
  confirmPassword(user, (body as { password?: unknown } | null)?.password)
  if (!token.secret) throw new MockError('FRM-API-1016')
  recordAudit(event, tenant, { action: 'api.token_revealed', actor: actorOf(user), resource: { type: 'api_token', id: token.id, name: token.name } })
  const secrets: ApiTokenSecrets = { ...(token.kind === 'static' ? { token: token.secret } : { client_secret: token.secret }), ...(token.signing_secret ? { signing_secret: token.signing_secret } : {}) }
  return ok(secrets)
})

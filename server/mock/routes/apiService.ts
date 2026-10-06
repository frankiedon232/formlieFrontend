/**
 * Mock API service management (F13 M1, docs/API-CONTRACT.md → API service). Admins only until F22.
 *
 *   GET    /api-service/settings          the organisation's address handle and base address
 *   GET    /api-services                  list (q, sort, filter[status])        · /insights
 *   GET    /api-services/:id              one                                  · POST · PATCH · DELETE
 *   POST   /api-services/:id/duplicate    a copy with copies of its endpoints (switched off)
 *   GET    /api-endpoints                 list (q, sort, filter[service|method|status]) · /insights
 *   GET    /api-endpoints/:id             one with its fields                  · POST · PATCH · DELETE
 *
 * Endpoint names are unique in the organisation (FRM-API-1001); an endpoint needs a published
 * form (FRM-API-1002). The form's own rules decide which questions can be sent: required
 * questions are always accepted on POST, read-only ones, files and calculated values never.
 */
import { z } from 'zod'
import type { ApiInsights, ApiServiceSettings, ApiUsage } from '#shared/types/apiService'
import { API_STATUSES } from '#shared/types/apiService'
import { checkEndpointName, endpointFieldsOf, API_PAGE_SIZE_MAX } from '#shared/utils/apiService/endpoints'
import { API_METHODS, type ApiMethod } from '#shared/utils/urls/public'
import { actorOf, recordAudit } from '../core/audit'
import { requireAdmin } from '../core/auth'
import { MockError, ok, paginate, filtersOf } from '../core/respond'
import { defineMockRoute } from '../core/route'
import { parseBody } from '../core/validate'
import { API_BASE_URL, apiOf, endpointUsage, saveApi, schemaOf, sumUsage, toEndpoint, toEndpointDetail, toService, type StoredApiEndpoint } from '../data/apiStore'
import { formsOf } from '../data/formStore'
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

export const apiSettings = defineMockRoute(({ event }) => {
  const { tenant } = requireAdmin(event)
  const settings: ApiServiceSettings = { api_key: apiOf(tenant).api_key, base_url: API_BASE_URL }
  return ok(settings)
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
    api.endpoints.push({ ...endpoint, id: crypto.randomUUID(), service_id: copy.id, name: freeName(api, endpoint.name), status: 'disabled', fields: endpoint.fields.map(field => ({ ...field })), methods: [...endpoint.methods], created_at: now(), updated_at: now() })
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
  api.endpoints = api.endpoints.filter(item => item.service_id !== service.id)
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
  if (!values.methods.length) throw new MockError('FRM-GEN-1002', [{ field: 'methods', message: 'required' }])
  const fields = endpointFieldsOf(schema, values.fields)
  const writes = values.methods.some(method => method === 'POST' || method === 'PUT')
  if (writes && !fields.some(field => field.accept)) throw new MockError('FRM-GEN-1002', [{ field: 'fields', message: 'accept' }])
  if (values.methods.includes('GET') && !fields.some(field => field.returned)) throw new MockError('FRM-GEN-1002', [{ field: 'fields', message: 'returned' }])
  return {
    service_id: values.service_id,
    name: values.name,
    description: values.description || null,
    form_id: form.id,
    version: values.version,
    methods: API_METHODS.filter(method => values.methods.includes(method)),
    fields: fields.map(({ key, accept, required, returned, filter }) => ({ key, accept, required, returned, filter })),
    page_size: values.page_size,
    status: values.status ?? 'active',
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

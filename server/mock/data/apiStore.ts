/**
 * API service in the mock (F13): per workspace its address handle (decision 61), services and
 * endpoints, kept in `.data/mock/api-service.json`. A few believable ones are seeded on the
 * workspace's published forms the first time it is read. Calls per day are stable made-up numbers
 * per endpoint (the real service counts them from its request log, M4); nothing calls them yet.
 */
import type { ApiEndpoint, ApiEndpointDetail, ApiService, ApiStatus, ApiUsage } from '#shared/types/apiService'
import { endpointFieldsOf, endpointNameFrom } from '#shared/utils/apiService/endpoints'
import type { FormSchemaV1 } from '#shared/utils/forms/schema'
import { API_METHODS, apiEndpointUrl, type ApiMethod } from '#shared/utils/urls/public'
import { loadPersisted, savePersisted } from '../core/persist'
import { seedOf } from './dataSourceSim'
import { formsOf, type StoredForm } from './formStore'
import { MOCK_USERS, type MockTenant } from './tenants'

export interface StoredApiService {
  id: string
  name: string
  description: string | null
  status: ApiStatus
  created_by: { id: string; name: string }
  created_at: string
  updated_at: string
}

export interface StoredApiEndpoint {
  id: string
  service_id: string
  name: string
  description: string | null
  form_id: string
  version: number | null
  methods: ApiMethod[]
  fields: { key: string; accept: boolean; required: boolean; returned: boolean; filter: boolean }[]
  page_size: number
  status: ApiStatus
  created_at: string
  updated_at: string
}

interface TenantApi {
  api_key: string
  services: StoredApiService[]
  endpoints: StoredApiEndpoint[]
}

const DAY = 86_400_000
export const API_BASE_URL = 'https://api.formalie.dev'
const stores = new Map<string, TenantApi>(Object.entries(loadPersisted<Record<string, TenantApi>>('api-service', {})))
export const saveApi = () => savePersisted('api-service', () => Object.fromEntries(stores))
const iso = (time: number) => new Date(time).toISOString()

/** A 10-character handle of letters and digits, stable per workspace in the mock. */
function handleFor(tenantId: string) {
  const chars = 'ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnpqrstuvwxyz23456789'
  return Array.from({ length: 10 }, (_, i) => chars[seedOf(`${tenantId}:api:${i}`) % chars.length]).join('')
}

const SEED_SERVICES = [
  { name: 'Customer onboarding', description: 'Sign-ups and account requests from the website and the mobile app.', status: 'active' as const },
  { name: 'Partner bookings', description: 'Bookings that partner systems send in and read back.', status: 'active' as const },
  { name: 'Internal tools', description: 'Back-office scripts; switched off while they are rebuilt.', status: 'disabled' as const },
]
const SEED_METHODS: ApiMethod[][] = [['POST'], ['GET', 'POST', 'PUT'], ['GET', 'POST', 'PUT', 'DELETE'], ['GET'], ['POST', 'GET']]

/** The workspace's API service (seeded once on its published forms). */
export function apiOf(tenant: MockTenant): TenantApi {
  let api = stores.get(tenant.id)
  if (!api) {
    const owner = MOCK_USERS.find(user => user.tenant_id === tenant.id && user.role === 'owner') ?? MOCK_USERS.find(user => user.tenant_id === tenant.id)
    const by = { id: owner?.id ?? 'system', name: owner ? `${owner.first_name} ${owner.last_name}` : 'Formalie' }
    const services = SEED_SERVICES.map((seed, i) => {
      const created = Date.now() - (150 - i * 10) * DAY
      return { id: crypto.randomUUID(), ...seed, created_by: by, created_at: iso(created), updated_at: iso(created + 2 * DAY) }
    })
    const forms = formsOf(tenant).forms.filter(form => !form.deleted_at && form.status === 'published').slice(0, 5)
    const endpoints: StoredApiEndpoint[] = forms.map((form, i) => {
      const created = Date.now() - (120 - i * 15) * DAY
      const schema = schemaOf(form, null)
      return {
        id: crypto.randomUUID(),
        service_id: services[i < 2 ? 0 : i < 4 ? 1 : 2]!.id,
        name: endpointNameFrom(form.name) || `form-${i + 1}`,
        description: null,
        form_id: form.id,
        version: null,
        methods: SEED_METHODS[i % SEED_METHODS.length]!,
        fields: schema ? endpointFieldsOf(schema).map(({ key, accept, required, returned, filter }) => ({ key, accept, required, returned, filter })) : [],
        page_size: 50,
        status: 'active',
        created_at: iso(created),
        updated_at: iso(created + DAY),
      }
    })
    api = { api_key: handleFor(tenant.id), services, endpoints }
    stores.set(tenant.id, api)
    saveApi()
  }
  return api
}

/** The schema an endpoint uses: its pinned version, else the latest published one. */
export function schemaOf(form: StoredForm, version: number | null): FormSchemaV1 | null {
  if (version != null) return form.versions?.find(item => item.number === version)?.schema ?? null
  return form.published_schema ?? null
}

/** 30 days of calls for an endpoint (none while it, its service or its form is off). */
function usageOf(endpoint: StoredApiEndpoint, live: boolean): ApiUsage {
  const seed = seedOf(endpoint.id)
  const base = 20 + (seed % 140)
  const today = Date.parse(new Date().toISOString().slice(0, 10))
  const created = Date.parse(endpoint.created_at)
  const day = (offset: number) => {
    const time = today - offset * DAY
    if (!live && offset < 12) return 0
    if (time < created) return 0
    const weekday = new Date(time).getUTCDay()
    const shape = weekday === 0 || weekday === 6 ? 0.35 : 1
    return Math.round(base * shape * (0.7 + (seedOf(`${endpoint.id}:${offset}`) % 60) / 100))
  }
  const daily = Array.from({ length: 30 }, (_, i) => ({ date: new Date(today - (29 - i) * DAY).toISOString().slice(0, 10), count: day(29 - i) }))
  const calls = daily.reduce((sum, item) => sum + item.count, 0)
  const previous = Array.from({ length: 30 }, (_, i) => day(30 + i)).reduce((sum, n) => sum + n, 0)
  const lastDay = [...daily].reverse().find(item => item.count)
  return {
    calls_30d: calls,
    previous_30d: previous,
    errors_30d: Math.round(calls * (0.01 + (seed % 5) / 100)),
    daily,
    avg_ms: calls ? 40 + (seed % 140) : null,
    // Some time on the last day with calls, never later than a few minutes ago
    last_call_at: lastDay ? iso(Math.min(Date.parse(lastDay.date) + 25_000_000 + (seed % 36_000_000), Date.now() - 120_000 - (seed % 3_000_000))) : null,
  }
}

const sumUsage = (list: ApiUsage[]): ApiUsage => {
  const daily = (list[0]?.daily ?? []).map((item, i) => ({ date: item.date, count: list.reduce((sum, usage) => sum + (usage.daily[i]?.count ?? 0), 0) }))
  const times = list.map(usage => usage.avg_ms).filter((n): n is number => n != null)
  return {
    calls_30d: list.reduce((sum, usage) => sum + usage.calls_30d, 0),
    previous_30d: list.reduce((sum, usage) => sum + usage.previous_30d, 0),
    errors_30d: list.reduce((sum, usage) => sum + usage.errors_30d, 0),
    daily: daily.length ? daily : Array.from({ length: 30 }, (_, i) => ({ date: new Date(Date.parse(new Date().toISOString().slice(0, 10)) - (29 - i) * DAY).toISOString().slice(0, 10), count: 0 })),
    avg_ms: times.length ? Math.round(times.reduce((sum, n) => sum + n, 0) / times.length) : null,
    last_call_at: list.map(usage => usage.last_call_at).filter((v): v is string => !!v).sort().at(-1) ?? null,
  }
}

export function endpointUsage(tenant: MockTenant, endpoint: StoredApiEndpoint): ApiUsage {
  const api = apiOf(tenant)
  const service = api.services.find(item => item.id === endpoint.service_id)
  const form = formsOf(tenant).forms.find(item => item.id === endpoint.form_id)
  return usageOf(endpoint, endpoint.status === 'active' && service?.status === 'active' && form?.status === 'published')
}

export function toEndpoint(tenant: MockTenant, endpoint: StoredApiEndpoint): ApiEndpoint {
  const api = apiOf(tenant)
  const service = api.services.find(item => item.id === endpoint.service_id)!
  const form = formsOf(tenant).forms.find(item => item.id === endpoint.form_id)
  return {
    id: endpoint.id,
    name: endpoint.name,
    description: endpoint.description,
    service: { id: service.id, name: service.name, status: service.status },
    form: { id: endpoint.form_id, name: form?.name ?? '', status: form?.deleted_at ? 'archived' : (form?.status ?? 'archived') },
    version: endpoint.version,
    methods: API_METHODS.filter(method => endpoint.methods.includes(method)),
    status: endpoint.status,
    url: apiEndpointUrl(API_BASE_URL, api.api_key, endpoint.name),
    fields_accepted: endpoint.methods.some(method => method === 'POST' || method === 'PUT') ? endpoint.fields.filter(field => field.accept).length : 0,
    fields_returned: endpoint.methods.includes('GET') ? endpoint.fields.filter(field => field.returned).length : 0,
    created_at: endpoint.created_at,
    updated_at: endpoint.updated_at,
    ...endpointUsage(tenant, endpoint),
  }
}

export function toEndpointDetail(tenant: MockTenant, endpoint: StoredApiEndpoint): ApiEndpointDetail {
  const form = formsOf(tenant).forms.find(item => item.id === endpoint.form_id)
  const schema = form ? schemaOf(form, endpoint.version) : null
  return {
    ...toEndpoint(tenant, endpoint),
    fields: schema ? endpointFieldsOf(schema, endpoint.fields) : [],
    page_size: endpoint.page_size,
    versions: (form?.versions ?? []).map(item => item.number).sort((a, b) => b - a),
  }
}

export function toService(tenant: MockTenant, service: StoredApiService): ApiService {
  const endpoints = apiOf(tenant).endpoints.filter(item => item.service_id === service.id)
  return {
    ...service,
    endpoints_count: endpoints.length,
    methods: API_METHODS.filter(method => endpoints.some(item => item.status === 'active' && item.methods.includes(method))),
    ...sumUsage(endpoints.map(item => endpointUsage(tenant, item))),
  }
}

export { sumUsage }

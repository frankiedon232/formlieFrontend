/**
 * API service in the mock (F13): per workspace its address handle (decision 61), services and
 * endpoints, kept in `.data/mock/api-service.json`. A few believable ones are seeded on the
 * workspace's published forms the first time it is read. Calls per day are stable made-up numbers
 * per endpoint (the real service counts them from its request log, M4); nothing calls them yet.
 * Tokens (M2): only a hash and the last 4 characters of each secret are kept; secrets are returned
 * once, when made. Data saved before M2 is brought up to date the first time it is read.
 */
import { createHash, randomBytes } from 'node:crypto'
import type { ApiEndpoint, ApiEndpointDetail, ApiService, ApiStatus, ApiToken, ApiTokenKind, ApiTokenMode, ApiTokenScopes, ApiUsage } from '#shared/types/apiService'
import { maskValue, secretPreview, tokenPrefix, tokenStatusOf } from '#shared/utils/apiService/tokens'
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
  /** Headers every call must send, with their values (F13 M2). */
  headers: { name: string; value: string }[]
  status: ApiStatus
  created_at: string
  updated_at: string
}

export interface StoredApiToken {
  id: string
  name: string
  kind: ApiTokenKind
  mode: ApiTokenMode
  /** SHA-256 of the secret (bearer token or client secret) and its visible preview. */
  secret_hash: string
  preview: string
  /** Before a rotation: the old secret's hash, valid until `rotating_until`. */
  previous_hash: string | null
  rotating_until: string | null
  client_id: string | null
  lifetime_minutes: number | null
  signing: boolean
  /** HMAC needs the secret itself: kept encrypted at rest by the real backend, plain in the mock. */
  signing_secret: string | null
  scopes: ApiTokenScopes
  expires_at: string | null
  last_used_at: string | null
  created_by: { id: string; name: string }
  created_at: string
  revoked_at: string | null
}

interface TenantApi {
  api_key: string
  previous_key?: string | null
  previous_until?: string | null
  rotated_at?: string | null
  services: StoredApiService[]
  endpoints: StoredApiEndpoint[]
  tokens?: StoredApiToken[]
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
export function apiOf(tenant: MockTenant): TenantApi & { tokens: StoredApiToken[] } {
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
        headers: [],
        status: 'active',
        created_at: iso(created),
        updated_at: iso(created + DAY),
      }
    })
    api = { api_key: handleFor(tenant.id), services, endpoints }
    stores.set(tenant.id, api)
    saveApi()
  }
  // Saved before M2: endpoints get their headers, the workspace its tokens
  if (!api.tokens) {
    for (const endpoint of api.endpoints) endpoint.headers ??= []
    api.tokens = seedTokens(api)
    saveApi()
  }
  return api as TenantApi & { tokens: StoredApiToken[] }
}

export const hashSecret = (secret: string) => createHash('sha256').update(secret).digest('hex')
const ALPHABET = 'ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnpqrstuvwxyz23456789'
/** A random secret with its prefix: 32 characters for tokens, 40 for client and signing secrets. */
export function newSecret(kind: ApiTokenKind | 'client_id' | 'signing', mode: ApiTokenMode) {
  const length = kind === 'static' ? 32 : kind === 'client_id' ? 16 : 40
  return tokenPrefix(kind, mode) + Array.from(randomBytes(length), byte => ALPHABET[byte % ALPHABET.length]).join('')
}

/** A few believable tokens: a live website token, a test partner client with signing, an expiring and a revoked one. */
function seedTokens(api: TenantApi): StoredApiToken[] {
  const by = api.services[0]?.created_by ?? { id: 'system', name: 'Formalie' }
  const make = (index: number, values: Partial<StoredApiToken> & Pick<StoredApiToken, 'name' | 'kind' | 'mode'>): StoredApiToken => {
    const secret = newSecret(values.kind, values.mode)
    const created = Date.now() - (100 - index * 18) * DAY
    return {
      id: crypto.randomUUID(),
      secret_hash: hashSecret(secret),
      preview: secretPreview(secret),
      previous_hash: null,
      rotating_until: null,
      client_id: values.kind === 'client' ? newSecret('client_id', values.mode) : null,
      lifetime_minutes: values.kind === 'client' ? 15 : null,
      signing: false,
      signing_secret: null,
      scopes: { services: [], endpoints: [], methods: [] },
      expires_at: null,
      last_used_at: iso(Date.now() - (index + 1) * 3_100_000),
      created_by: by,
      created_at: iso(created),
      revoked_at: null,
      ...values,
    }
  }
  const [first, second] = api.services
  return [
    make(0, { name: 'Website sign-ups', kind: 'static', mode: 'live', scopes: { services: first ? [first.id] : [], endpoints: [], methods: ['POST'] } }),
    make(1, { name: 'Partner sandbox', kind: 'client', mode: 'test', signing: true, signing_secret: newSecret('signing', 'test'), scopes: { services: second ? [second.id] : [], endpoints: [], methods: [] } }),
    make(2, { name: 'Mobile app', kind: 'static', mode: 'live', expires_at: iso(Date.now() + 9 * DAY) }),
    make(3, { name: 'Old import script', kind: 'static', mode: 'live', revoked_at: iso(Date.now() - 20 * DAY), last_used_at: iso(Date.now() - 24 * DAY) }),
  ]
}

/** 30 days of calls for a token (none once revoked or expired). */
function tokenUsage(token: StoredApiToken): ApiUsage {
  const seed = seedOf(token.id)
  const base = 15 + (seed % 120)
  const today = Date.parse(new Date().toISOString().slice(0, 10))
  const created = Date.parse(token.created_at)
  const stopped = token.revoked_at ? Date.parse(token.revoked_at) : token.expires_at && Date.parse(token.expires_at) < Date.now() ? Date.parse(token.expires_at) : Infinity
  const day = (offset: number) => {
    const time = today - offset * DAY
    if (time < created || time > stopped) return 0
    const weekday = new Date(time).getUTCDay()
    return Math.round(base * (weekday === 0 || weekday === 6 ? 0.3 : 1) * (0.7 + (seedOf(`${token.id}:${offset}`) % 60) / 100))
  }
  const daily = Array.from({ length: 30 }, (_, i) => ({ date: new Date(today - (29 - i) * DAY).toISOString().slice(0, 10), count: day(29 - i) }))
  const calls = daily.reduce((sum, item) => sum + item.count, 0)
  return {
    calls_30d: calls,
    previous_30d: Array.from({ length: 30 }, (_, i) => day(30 + i)).reduce((sum, n) => sum + n, 0),
    errors_30d: Math.round(calls * (0.005 + (seed % 4) / 100)),
    daily,
    avg_ms: calls ? 50 + (seed % 120) : null,
    last_call_at: token.last_used_at,
  }
}

export function toToken(tenant: MockTenant, token: StoredApiToken): ApiToken {
  const api = apiOf(tenant)
  return {
    id: token.id,
    name: token.name,
    kind: token.kind,
    mode: token.mode,
    status: tokenStatusOf(token),
    preview: token.kind === 'client' ? token.client_id! : token.preview,
    client_id: token.client_id,
    lifetime_minutes: token.lifetime_minutes,
    signing: token.signing,
    scopes: token.scopes,
    scope_names: {
      services: token.scopes.services.map(id => api.services.find(item => item.id === id)?.name).filter((name): name is string => !!name),
      endpoints: token.scopes.endpoints.map(id => api.endpoints.find(item => item.id === id)?.name).filter((name): name is string => !!name),
    },
    expires_at: token.expires_at,
    rotating_until: token.rotating_until && Date.parse(token.rotating_until) > Date.now() ? token.rotating_until : null,
    last_used_at: token.last_used_at,
    created_by: token.created_by,
    created_at: token.created_at,
    revoked_at: token.revoked_at,
    ...tokenUsage(token),
  }
}

export { maskValue }

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
    required_headers: (endpoint.headers ?? []).map(header => header.name),
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
    headers: (endpoint.headers ?? []).map(header => ({ name: header.name, preview: maskValue(header.value) })),
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

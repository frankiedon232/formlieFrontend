/**
 * API service in the mock (F13): per workspace its address handle (decision 61), services and
 * endpoints, kept in `.data/mock/api-service.json`. A few believable ones are seeded on the
 * workspace's published forms the first time it is read. Calls per day are stable made-up numbers
 * per endpoint (the real service counts them from its request log, M4); nothing calls them yet.
 * Tokens (M2): only a hash and the last 4 characters of each secret are kept; secrets are returned
 * once, when made. Data saved before M2 is brought up to date the first time it is read.
 */
import { createHash, randomBytes } from 'node:crypto'
import type { ApiAccessRule, ApiEndpoint, ApiEndpointDetail, ApiEndpointSetup, ApiRateLimits, ApiRuleAction, ApiRuleKind, ApiService, ApiStatus, ApiToken, ApiTokenKind, ApiTokenMode, ApiTokenScopes, ApiUsage } from '#shared/types/apiService'
import { maskValue, scopeAllows, secretPreview, tokenPrefix, tokenReach, tokenStatusOf } from '#shared/utils/apiService/tokens'
import { rulesFor } from '#shared/utils/apiService/access'
import { channelsOf } from '#shared/types/forms'
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
  /** Allowed websites for browser callers (leftovers L6); missing on services made before = none. */
  allowed_origins?: string[]
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
  fields: { key: string; name?: string; accept: boolean; required: boolean; returned: boolean; filter: boolean }[]
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
  /** The secret itself, so it can be shown again after the password (owner, 2026-10-06): encrypted at rest by the backend, plain in the mock. Missing on tokens made before. */
  secret?: string | null
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

export interface StoredAccessRule {
  id: string
  action: ApiRuleAction
  kind: ApiRuleKind
  values: string[]
  scope: { type: 'all' | 'service' | 'endpoint'; id: string | null }
  note: string | null
  enabled: boolean
  /** Calls the rule decided, per day (made-up history for seeded rules, plus real calls). */
  hits: Record<string, number>
  last_hit_at: string | null
  created_by: { id: string; name: string }
  created_at: string
  updated_at: string
}

interface TenantApi {
  api_key: string
  previous_key?: string | null
  previous_until?: string | null
  rotated_at?: string | null
  services: StoredApiService[]
  endpoints: StoredApiEndpoint[]
  tokens?: StoredApiToken[]
  rules?: StoredAccessRule[]
  limits?: ApiRateLimits
  /** Calls refused by a rate limit, per day. */
  limited?: Record<string, number>
  /** Request log: keep request and response bodies (personal answers masked). */
  logging?: { keep_bodies: boolean; days: number }
  /** POSTs by Formalie-Key for 24 hours: a retry answers with its first record, a different body is refused. */
  replays?: StoredReplay[]
}

export interface StoredReplay {
  /** `{endpoint id}:{Formalie-Key}` */
  key: string
  /** SHA-256 of the body as canonical JSON. */
  hash: string
  at: string
  response_id: string | null
  /** Test tokens store nothing: the answer they got, to give it again. */
  answer?: unknown
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
export function apiOf(tenant: MockTenant): TenantApi & { tokens: StoredApiToken[]; rules: StoredAccessRule[]; limits: ApiRateLimits; limited: Record<string, number> } {
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
        fields: schema ? endpointFieldsOf(schema).map(({ key, name, accept, required, returned, filter }) => ({ key, name, accept, required, returned, filter })) : [],
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
  // Before the Formalie prefixes (owner, 2026-10-06): the sample tokens (nobody has their secrets) get new ones
  const SEEDED = ['Website sign-ups', 'Partner sandbox', 'Mobile app', 'Old import script']
  for (const token of api.tokens ?? []) {
    // No management API any more (owner, 2026-10-06): its rights go
    if ('manage' in token.scopes) {
      delete (token.scopes as { manage?: unknown }).manage
      saveApi()
    }
    // No signed calls any more (owner, 2026-10-06: three headers, nothing else)
    if (token.signing || token.signing_secret) {
      token.signing = false
      token.signing_secret = null
      saveApi()
    }
    // Before secrets could be viewed again (owner, 2026-10-06): the samples get a viewable one
    if (SEEDED.includes(token.name) && token.preview.startsWith('formalie_') && token.secret === undefined) {
      const fresh = newSecret(token.kind, token.mode)
      token.secret_hash = hashSecret(fresh)
      token.secret = fresh
      token.preview = secretPreview(fresh)
      saveApi()
      continue
    }
    if (!SEEDED.includes(token.name) || token.preview.startsWith('formalie_')) continue
    const secret = newSecret(token.kind, token.mode)
    token.secret_hash = hashSecret(secret)
    token.secret = secret
    token.preview = secretPreview(secret)
    if (token.client_id) token.client_id = newSecret('client_id', token.mode)
    saveApi()
  }
  // No custom headers any more (owner, 2026-10-06): endpoints lose theirs
  for (const endpoint of api.endpoints) {
    if (!endpoint.headers?.length) continue
    endpoint.headers = []
    saveApi()
  }
  // Before API names (owner, 2026-10-06): every endpoint gets clean names from the labels, once, then they stay
  for (const endpoint of api.endpoints) {
    if (endpoint.fields.every(field => field.name)) continue
    const form = formsOf(tenant).forms.find(item => item.id === endpoint.form_id)
    const schema = form ? schemaOf(form, endpoint.version) : null
    if (!schema) continue
    const named = new Map(endpointFieldsOf(schema, endpoint.fields).map(field => [field.key, field.name]))
    endpoint.fields = endpoint.fields.map(field => ({ ...field, name: named.get(field.key) ?? field.key }))
    saveApi()
  }
  // Saved before M3: access rules and rate limits
  if (!api.rules || !api.limits) {
    api.rules ??= seedRules(api)
    api.limits ??= { per_token: 600, per_ip: 120, per_endpoint: 1200, updated_at: null }
    api.limited ??= {}
    saveApi()
  }
  return api as TenantApi & { tokens: StoredApiToken[]; rules: StoredAccessRule[]; limits: ApiRateLimits; limited: Record<string, number> }
}

/** Sample rules that never get in the way of testing: blocks on documentation addresses, and a website-only rule switched off. */
function seedRules(api: TenantApi): StoredAccessRule[] {
  const by = api.services[0]?.created_by ?? { id: 'system', name: 'Formalie' }
  const hits = (seed: string, base: number) => {
    const out: Record<string, number> = {}
    for (let i = 0; i < 30; i++) {
      const count = Math.round(base * ((seedOf(`${seed}:${i}`) % 100) / 100))
      if (count) out[new Date(Date.now() - i * DAY).toISOString().slice(0, 10)] = count
    }
    return out
  }
  const at = (days: number) => iso(Date.now() - days * DAY)
  const website = api.services[0]
  return [
    { id: crypto.randomUUID(), action: 'block', kind: 'ip', values: ['192.0.2.66', '198.51.100.0/28'], scope: { type: 'all', id: null }, note: 'Seen scraping; blocked everywhere.', enabled: true, hits: hits('block-ip', 14), last_hit_at: at(0.2), created_by: by, created_at: at(40), updated_at: at(40) },
    { id: crypto.randomUUID(), action: 'block', kind: 'domain', values: ['*.spam-example.net'], scope: { type: 'all', id: null }, note: null, enabled: true, hits: hits('block-domain', 5), last_hit_at: at(2), created_by: by, created_at: at(25), updated_at: at(25) },
    { id: crypto.randomUUID(), action: 'allow', kind: 'domain', values: ['example.com', '*.example.com'], scope: { type: website ? 'service' : 'all', id: website?.id ?? null }, note: 'Website only: switch on when the new site is live.', enabled: false, hits: {}, last_hit_at: null, created_by: by, created_at: at(10), updated_at: at(10) },
  ]
}

export function toRule(tenant: MockTenant, rule: StoredAccessRule): ApiAccessRule {
  const api = apiOf(tenant)
  const today = Date.parse(new Date().toISOString().slice(0, 10))
  const daily = Array.from({ length: 30 }, (_, i) => {
    const date = new Date(today - (29 - i) * DAY).toISOString().slice(0, 10)
    return { date, count: rule.hits[date] ?? 0 }
  })
  const name = rule.scope.type === 'service' ? (api.services.find(item => item.id === rule.scope.id)?.name ?? null) : rule.scope.type === 'endpoint' ? (api.endpoints.find(item => item.id === rule.scope.id)?.name ?? null) : null
  return {
    id: rule.id,
    action: rule.action,
    kind: rule.kind,
    values: rule.values,
    scope: { ...rule.scope, name },
    note: rule.note,
    enabled: rule.enabled,
    hits_30d: daily.reduce((sum, day) => sum + day.count, 0),
    daily,
    last_hit_at: rule.last_hit_at,
    created_by: rule.created_by,
    created_at: rule.created_at,
    updated_at: rule.updated_at,
  }
}

export const hashSecret = (secret: string) => createHash('sha256').update(secret).digest('hex')
const ALPHABET = 'ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnpqrstuvwxyz23456789'
/** A random secret with its prefix: 32 characters for tokens, 40 for client and signing secrets. */
export function newSecret(kind: ApiTokenKind | 'client_id' | 'signing', mode: ApiTokenMode) {
  const length = kind === 'static' ? 32 : kind === 'client_id' ? 16 : 40
  return tokenPrefix(kind, mode) + Array.from(randomBytes(length), byte => ALPHABET[byte % ALPHABET.length]).join('')
}

/** A few believable tokens: a live website token, a test partner client, an expiring and a revoked one. */
function seedTokens(api: TenantApi): StoredApiToken[] {
  const by = api.services[0]?.created_by ?? { id: 'system', name: 'Formalie' }
  const make = (index: number, values: Partial<StoredApiToken> & Pick<StoredApiToken, 'name' | 'kind' | 'mode'>): StoredApiToken => {
    const secret = newSecret(values.kind, values.mode)
    const created = Date.now() - (100 - index * 18) * DAY
    return {
      id: crypto.randomUUID(),
      secret_hash: hashSecret(secret),
      secret,
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
  return [make(0, { name: 'Website sign-ups', kind: 'static', mode: 'live', scopes: { services: first ? [first.id] : [], endpoints: [], methods: ['POST'] } }), make(1, { name: 'Partner sandbox', kind: 'client', mode: 'test', signing: false, signing_secret: null, scopes: { services: second ? [second.id] : [], endpoints: [], methods: [] } }), make(2, { name: 'Mobile app', kind: 'static', mode: 'live', expires_at: iso(Date.now() + 9 * DAY) }), make(3, { name: 'Old import script', kind: 'static', mode: 'live', revoked_at: iso(Date.now() - 20 * DAY), last_used_at: iso(Date.now() - 24 * DAY) })]
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
    viewable: !!token.secret && !token.revoked_at,
    // Services or endpoints in its scope that were deleted: kept (dropping them would widen the token), shown as such
    scope_gone: token.scopes.services.filter(id => !api.services.some(item => item.id === id)).length + token.scopes.endpoints.filter(id => !api.endpoints.some(item => item.id === id)).length,
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
    headers: (endpoint.headers ?? []).map(header => ({ name: header.name, preview: maskValue(header.value), value: header.value })),
    versions: (form?.versions ?? []).map(item => item.number).sort((a, b) => b - a),
    setup: endpointSetup(tenant, endpoint, form),
  }
}

/** How far the endpoint is set up (owner, 2026-10-06): service on, form published, tokens that can call it, access rules, live. */
function endpointSetup(tenant: MockTenant, endpoint: StoredApiEndpoint, form: StoredForm | undefined): ApiEndpointSetup {
  const api = apiOf(tenant)
  const callers = api.tokens.filter(token => token.kind !== 'webhook' && tokenStatusOf(token) !== 'revoked' && tokenStatusOf(token) !== 'expired' && endpoint.methods.some(method => scopeAllows(token.scopes, { endpoint_id: endpoint.id, service_id: endpoint.service_id, method })))
  return {
    service_active: api.services.find(item => item.id === endpoint.service_id)?.status === 'active',
    form_published: form?.status === 'published',
    form_api: !!form && channelsOf(form).includes('api'),
    // Made for it (this endpoint, or its whole service) apart from tokens for everything (owner 2026-10-08)
    tokens_live: callers.filter(token => token.mode === 'live' && tokenReach(token.scopes, endpoint) !== 'all').length,
    tokens_test: callers.filter(token => token.mode === 'test' && tokenReach(token.scopes, endpoint) !== 'all').length,
    tokens_all_live: callers.filter(token => token.mode === 'live' && tokenReach(token.scopes, endpoint) === 'all').length,
    tokens_all_test: callers.filter(token => token.mode === 'test' && tokenReach(token.scopes, endpoint) === 'all').length,
    signing_tokens: callers.filter(token => token.signing).length,
    rules: rulesFor(api.rules, endpoint).filter(rule => rule.enabled).length,
    live: endpoint.status === 'active',
  }
}

export function toService(tenant: MockTenant, service: StoredApiService): ApiService {
  const endpoints = apiOf(tenant).endpoints.filter(item => item.service_id === service.id)
  return {
    ...service,
    allowed_origins: service.allowed_origins ?? [],
    endpoints_count: endpoints.length,
    methods: API_METHODS.filter(method => endpoints.some(item => item.status === 'active' && item.methods.includes(method))),
    ...sumUsage(endpoints.map(item => endpointUsage(tenant, item))),
  }
}

export { sumUsage }

/** A new token with its secret (the token route and webhooks both make them here). Returns the token and its secret. */
export function createToken(tenant: MockTenant, values: { name: string; kind: ApiTokenKind; mode: ApiTokenMode; scopes: ApiTokenScopes; expires_at: string | null; lifetime_minutes?: number | null }, by: { id: string; name: string }) {
  const secret = newSecret(values.kind, values.mode)
  const token: StoredApiToken = {
    id: crypto.randomUUID(),
    name: values.name,
    kind: values.kind,
    mode: values.mode,
    secret_hash: hashSecret(secret),
    secret,
    preview: secretPreview(secret),
    previous_hash: null,
    rotating_until: null,
    client_id: values.kind === 'client' ? newSecret('client_id', values.mode) : null,
    lifetime_minutes: values.kind === 'client' ? (values.lifetime_minutes ?? 15) : null,
    signing: false,
    signing_secret: null,
    // A webhook token calls nothing: no scope at all
    scopes: values.kind === 'webhook' ? { services: [], endpoints: [], methods: [] } : values.scopes,
    expires_at: values.expires_at,
    last_used_at: null,
    created_by: by,
    created_at: new Date().toISOString(),
    revoked_at: null,
  }
  apiOf(tenant).tokens.unshift(token)
  saveApi()
  return { token, secret }
}

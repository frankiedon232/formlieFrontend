/**
 * API service (F13, docs/API-CONTRACT.md → API service): services group endpoints; an endpoint
 * turns one form into an API at `https://api.formalie.dev/{apiKey}/{endpoint}`. Data sent to it
 * goes through the form's own checks and lands where the form's responses are kept.
 */
import type { FormStatus } from './forms'
import type { ApiMethod } from '#shared/utils/urls/public'

export const API_STATUSES = ['active', 'disabled'] as const
export type ApiStatus = (typeof API_STATUSES)[number]

/** Calls in the last 30 days (the numbers every list shows). */
export interface ApiUsage {
  calls_30d: number
  previous_30d: number
  errors_30d: number
  daily: { date: string; count: number }[]
  /** Median answer time, ms. */
  avg_ms: number | null
  last_call_at: string | null
}

export interface ApiService extends ApiUsage {
  id: string
  name: string
  description: string | null
  status: ApiStatus
  endpoints_count: number
  /** Methods switched on in any of its endpoints. */
  methods: ApiMethod[]
  created_by: { id: string; name: string }
  created_at: string
  updated_at: string
}

export interface ApiServiceSaveRequest {
  name: string
  description?: string | null
  status?: ApiStatus
}

/** One question of the form, as the endpoint uses it. */
export interface ApiEndpointField {
  /** The question's key in the form (internal: stored answers, tables, exports). */
  key: string
  /** Its name in the API's payloads and answers (owner, 2026-10-06): from the label (`first_name`), editable per endpoint. */
  name: string
  label: string
  type: string
  page: number
  /** The form requires it (then POST requires it too). */
  form_required: boolean
  /** Can be sent at all (not read-only, calculated, a file or a payment). */
  acceptable: boolean
  /** Can narrow a GET list (choices, dates, numbers, short text, email). */
  filterable: boolean
  accept: boolean
  required: boolean
  returned: boolean
  filter: boolean
  /** The question's answer values (choices), so examples and docs show real ones (M5); `parent` = the value above it (list with levels). */
  options?: { value: string; label: string; parent?: string }[]
  /** A large list (F15 M5): `options` holds examples, this is how many there are. */
  options_total?: number
  /** A level of a list with levels (F15 M2): the key of the question one level up. Only values under what was sent for it are accepted; with nothing under it, it isn't asked (not required). */
  depends_on?: string
}

export interface ApiEndpoint extends ApiUsage {
  id: string
  /** The address part: lower-case words joined by hyphens. */
  name: string
  description: string | null
  service: { id: string; name: string; status: ApiStatus }
  form: { id: string; name: string; status: FormStatus }
  /** Pinned form version; null = always the latest published version. */
  version: number | null
  methods: ApiMethod[]
  status: ApiStatus
  url: string
  fields_accepted: number
  fields_returned: number
  /** Names of the headers it requires. */
  required_headers: string[]
  created_at: string
  updated_at: string
}

export interface ApiEndpointDetail extends ApiEndpoint {
  fields: ApiEndpointField[]
  /** Largest page a GET list returns (≤ 100). */
  page_size: number
  /** Headers every call must send (F13 M2). */
  headers: ApiHeaderRule[]
  /** Published versions the endpoint can be pinned to (newest first). */
  versions: number[]
  /** How far it is set up (guided setup, F13 M7). */
  setup: ApiEndpointSetup
}

/** The guided setup's steps, in order (F13 M7). */
export type ApiJourneyStep = 'service' | 'endpoint' | 'token' | 'access' | 'live'

/** The organisation's setup so far (guided setup, F13 M7). */
export interface ApiSetupSummary {
  services: number
  endpoints: number
  endpoints_live: number
  tokens_live: number
  tokens_test: number
  rules: number
}

/** How a token or access rule reaches an item: made for this endpoint, for its whole service, or for everything. */
export type ApiReach = 'endpoint' | 'service' | 'all'

/** What an API item is connected to (detail panels, owner 2026-10-08): GET /api-service/connections?type=&id= */
export interface ApiConnections {
  service: { id: string; name: string; status: string } | null
  form: { id: string; name: string; status: string } | null
  endpoints: { id: string; name: string; status: string; service: string }[]
  tokens: { id: string; name: string; mode: 'live' | 'test'; status: string; reach: ApiReach }[]
  rules: { id: string; action: 'allow' | 'block'; kind: string; values: string[]; enabled: boolean; reach: ApiReach }[]
}

export interface ApiEndpointSetup {
  service_active: boolean
  form_published: boolean
  /** The form is open to the API service (its channels, owner 2026-10-06). */
  form_api: boolean
  /** Tokens (not revoked or expired) made for it: scoped to this endpoint or to its service (owner 2026-10-08). */
  tokens_live: number
  tokens_test: number
  /** Tokens for every endpoint (no service or endpoint chosen) that can call it too, counted apart so none look assigned. */
  tokens_all_live: number
  tokens_all_test: number
  /** Of those, tokens with signed calls on: their calls also need X-Formalie-Timestamp and X-Formalie-Signature. */
  signing_tokens: number
  /** Switched-on access rules that apply to it. */
  rules: number
  live: boolean
}

export interface ApiEndpointSaveRequest {
  name: string
  description?: string | null
  service_id: string
  form_id: string
  version: number | null
  methods: ApiMethod[]
  fields: { key: string; name?: string; accept: boolean; required: boolean; returned: boolean; filter: boolean }[]
  page_size: number
  headers?: ApiHeaderInput[]
  status?: ApiStatus
}

/** The chart cards of Services and Endpoints. */
export interface ApiInsights {
  total: number
  by_status: Record<ApiStatus, number>
  by_method: Record<ApiMethod, number>
  calls_30d: number
  previous_30d: number
  errors_30d: number
  daily: { date: string; count: number }[]
  avg_ms: number | null
}

/** The organisation's address handle (decision 61) and the API's base address. */
export interface ApiServiceSettings {
  api_key: string
  base_url: string
  /** After rotating the address key, the old one keeps working until `previous_until`. */
  previous_key: string | null
  previous_until: string | null
  rotated_at: string | null
}

// ── Tokens (F13 M2) ──────────────────────────────────────────────────────────────────────

/** Test tokens never touch live data (the try-it console and sandboxes, M5); live tokens do. */
export const API_TOKEN_MODES = ['live', 'test'] as const
export type ApiTokenMode = (typeof API_TOKEN_MODES)[number]
/** A long-lived bearer token, or a client id + secret that gets short-lived tokens from `/{apiKey}/token`. */
/** How a token signs in: a bearer token, a client id + secret, or (owner, 2026-10-06) a webhook token, which only
 * identifies Formalie's calls to a webhook's address and can never call the API. */
export type ApiTokenKind = 'static' | 'client' | 'webhook'
export const API_TOKEN_STATUSES = ['active', 'expiring', 'expired', 'revoked'] as const
export type ApiTokenStatus = (typeof API_TOKEN_STATUSES)[number]

/** What a token may call; an empty list means "all". */
export interface ApiTokenScopes {
  services: string[]
  endpoints: string[]
  methods: ApiMethod[]
}

export interface ApiToken extends ApiUsage {
  id: string
  name: string
  kind: ApiTokenKind
  mode: ApiTokenMode
  status: ApiTokenStatus
  /** The visible part: its prefix and last 4 characters (`formalie_live_…a1B2`), or the client id. */
  preview: string
  client_id: string | null
  /** Client credentials: minutes a short-lived token lasts. */
  lifetime_minutes: number | null
  /** Calls must be signed (HMAC-SHA256, SECURITY-PROTOCOL §9). */
  signing: boolean
  scopes: ApiTokenScopes
  /** Readable scope names (services, endpoints) for lists. */
  scope_names: { services: string[]; endpoints: string[] }
  expires_at: string | null
  /** After a rotation the old secret keeps working until then. */
  rotating_until: string | null
  last_used_at: string | null
  created_by: { id: string; name: string }
  created_at: string
  revoked_at: string | null
  /** Its secret can be shown again (after the password); false for tokens made before that existed. */
  viewable: boolean
  /** Deleted services or endpoints still in its scope (it can not call them; never widened to everything). */
  scope_gone: number
}

export interface ApiTokenSaveRequest {
  name: string
  kind: ApiTokenKind
  mode: ApiTokenMode
  scopes: ApiTokenScopes
  expires_at: string | null
  lifetime_minutes?: number | null
}

/** Secrets are shown once, right after creating or rotating; Formalie keeps only a hash. */
export interface ApiTokenSecrets {
  token?: string
  client_secret?: string
}
export interface ApiTokenCreated {
  token: ApiToken
  secrets: ApiTokenSecrets
}

export interface ApiTokenInsights {
  total: number
  by_status: Record<ApiTokenStatus, number>
  by_mode: Record<ApiTokenMode, number>
  calls_30d: number
  previous_30d: number
  daily: { date: string; count: number }[]
  /** Tokens unused for 90 days (worth revoking). */
  unused_90d: number
}

/** A header every call to an endpoint must send, with the value it must have (stored hashed is not needed: it is not a credential). */
export interface ApiHeaderRule {
  name: string
  /** Shown masked except its last 4 characters. */
  preview: string
  /** The value itself, for ready-to-copy examples in Docs & testing and Try it (admins only, owner 2026-10-06). */
  value: string
}
export interface ApiHeaderInput {
  name: string
  /** null keeps the saved value (editing). */
  value: string | null
}
/** A required header while editing an endpoint: `value` null keeps the saved one (shown as `preview`). */
export interface ApiHeaderDraft {
  name: string
  value: string | null
  preview: string | null
}

// ── Access rules and rate limits (F13 M3) ────────────────────────────────────────────────

export const API_RULE_KINDS = ['ip', 'domain', 'country', 'region', 'network'] as const
/** Anonymous networks an IP can belong to (IP intelligence on the server): VPN exits, open proxies, Tor exits, hosting / cloud providers. */
export const API_NETWORKS = ['vpn', 'proxy', 'tor', 'hosting'] as const
export type ApiNetwork = (typeof API_NETWORKS)[number]
export type ApiRuleKind = (typeof API_RULE_KINDS)[number]
export type ApiRuleAction = 'allow' | 'block'
/** Where a rule applies: everywhere, one service or one endpoint. */
export interface ApiRuleScope {
  type: 'all' | 'service' | 'endpoint'
  id: string | null
  name: string | null
}

export interface ApiAccessRule {
  id: string
  action: ApiRuleAction
  kind: ApiRuleKind
  /** IP addresses or ranges, domains (`*.example.com`), ISO countries or regions (continents). */
  values: string[]
  scope: ApiRuleScope
  note: string | null
  enabled: boolean
  /** Calls this rule decided in the last 30 days (allowed in, or refused). */
  hits_30d: number
  daily: { date: string; count: number }[]
  last_hit_at: string | null
  created_by: { id: string; name: string }
  created_at: string
  updated_at: string
}

export interface ApiAccessRuleSaveRequest {
  action: ApiRuleAction
  kind: ApiRuleKind
  values: string[]
  scope: { type: ApiRuleScope['type']; id: string | null }
  note?: string | null
  enabled?: boolean
}

export interface ApiAccessInsights {
  total: number
  by_action: Record<ApiRuleAction, number>
  by_kind: Record<ApiRuleKind, number>
  /** Calls refused by rules in the last 30 days. */
  refused_30d: number
  previous_30d: number
  daily: { date: string; count: number }[]
  limited_30d: number
}

/** Calls per minute; null = no limit. */
export interface ApiRateLimits {
  per_token: number | null
  per_ip: number | null
  per_endpoint: number | null
  updated_at: string | null
}

/** POST /api-access-rules/test: would this caller get in? */
export interface ApiAccessTestRequest {
  endpoint_id: string
  ip: string
  origin?: string | null
  country?: string | null
  networks?: ApiNetwork[]
}
export interface ApiAccessTestResult {
  allowed: boolean
  reason: 'blocked' | 'not_allowed' | null
  rule: { id: string; action: ApiRuleAction; value: string; kind: ApiRuleKind; scope: ApiRuleScope } | null
  /** Rules that applied to the endpoint, in the order they were checked. */
  checked: number
  region: string | null
}

// ── Request logs and analytics (F13 M4) ──────────────────────────────────────────────────

/** One call to the public API, as the request log keeps it (never the token itself). */
export interface ApiLogEntry {
  id: string
  at: string
  method: string
  /** `/{apiKey}/{endpoint}[/{id}]` */
  path: string
  status: number
  /** FRM-* code of a refused call. */
  code: string | null
  duration_ms: number
  endpoint: { id: string; name: string } | null
  service: { id: string; name: string } | null
  token: { id: string; name: string; mode: ApiTokenMode } | null
  ip: string
  country: string | null
  user_agent: string
  request_id: string
}

export interface ApiLogDetail extends ApiLogEntry {
  /** Only when "keep bodies" is on; personal answers masked. */
  request_body: unknown | null
  response_body: unknown | null
  /** Headers the caller sent, values of secrets masked. */
  request_headers: Record<string, string>
  bodies_kept: boolean
}

export interface ApiLogInsights {
  calls_30d: number
  previous_30d: number
  errors_30d: number
  daily: { date: string; count: number }[]
  by_class: Record<'2xx' | '4xx' | '5xx', number>
  avg_ms: number | null
}

export interface ApiLogSettings {
  /** Keep request and response bodies (personal answers masked) for `days`. */
  keep_bodies: boolean
  days: number
}

/** GET /api-analytics?from&to: the API service's own analytics. */
export interface ApiAnalytics {
  from: string
  to: string
  totals: { calls: number; errors: number; p50_ms: number | null; p95_ms: number | null; tokens_used: number }
  previous: { calls: number; errors: number; p50_ms: number | null; p95_ms: number | null; tokens_used: number }
  daily: { date: string; calls: number; errors: number }[]
  endpoints: { id: string; name: string; service: string; calls: number; errors: number; p95_ms: number | null; trend: number[] }[]
  tokens: { id: string; name: string; mode: ApiTokenMode; calls: number; errors: number }[]
  countries: { code: string; calls: number }[]
  methods: Record<ApiMethod, number>
}

// ── Docs console (F13 M5) ────────────────────────────────────────────────────────────────

/** POST /api-endpoints/{id}/try: one call through the real checks with a test token (nothing is stored). */
export interface ApiTryRequest {
  method: ApiMethod
  record_id?: string | null
  body?: unknown
  headers?: Record<string, string>
}
export interface ApiTryResult {
  status: number
  duration_ms: number
  headers: Record<string, string>
  body: unknown
}

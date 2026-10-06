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
  key: string
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
}

export interface ApiEndpointSaveRequest {
  name: string
  description?: string | null
  service_id: string
  form_id: string
  version: number | null
  methods: ApiMethod[]
  fields: { key: string; accept: boolean; required: boolean; returned: boolean; filter: boolean }[]
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
export type ApiTokenKind = 'static' | 'client'
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
  /** The visible part: its prefix and last 4 characters (`fml_live_…a1B2`), or the client id. */
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
}

export interface ApiTokenSaveRequest {
  name: string
  kind: ApiTokenKind
  mode: ApiTokenMode
  scopes: ApiTokenScopes
  expires_at: string | null
  lifetime_minutes?: number | null
  signing?: boolean
}

/** Secrets are shown once, right after creating or rotating; Formalie keeps only a hash. */
export interface ApiTokenSecrets {
  token?: string
  client_secret?: string
  signing_secret?: string
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

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
  created_at: string
  updated_at: string
}

export interface ApiEndpointDetail extends ApiEndpoint {
  fields: ApiEndpointField[]
  /** Largest page a GET list returns (≤ 100). */
  page_size: number
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
}

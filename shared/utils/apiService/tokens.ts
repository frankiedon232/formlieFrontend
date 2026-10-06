/**
 * Token and header rules shared by the portal and the server (F13 M2, SECURITY-PROTOCOL §9): token
 * prefixes (test / live told apart at a glance, and by secret scanners), status from the dates,
 * the visible preview of a secret, scope checks and the names allowed for required headers.
 */
import type { ApiTokenKind, ApiTokenMode, ApiTokenScopes, ApiTokenStatus } from '#shared/types/apiService'
import type { ApiMethod } from '#shared/utils/urls/public'

/**
 * Every secret says Formalie (owner, 2026-10-06): `formalie_live_` / `formalie_test_` (bearer tokens),
 * `formalie_client_…` (client ids), `formalie_secret_…` (client secrets), `formalie_sign_…` (signing
 * secrets), `formalie_access_…` (short-lived tokens from the token address).
 */
export function tokenPrefix(kind: ApiTokenKind | 'client_id' | 'signing' | 'access', mode: ApiTokenMode) {
  const part = kind === 'static' ? '' : kind === 'client' ? 'secret_' : kind === 'client_id' ? 'client_' : kind === 'signing' ? 'sign_' : kind === 'webhook' ? 'hook_' : 'access_'
  return `formalie_${part}${mode}_`
}

/** The visible part of a secret: its prefix and last 4 characters. */
export function secretPreview(secret: string) {
  const prefix = /^formalie_(?:[a-z]+_)?(?:live|test)_/.exec(secret)?.[0] ?? ''
  return `${prefix}…${secret.slice(-4)}`
}

/** A header value shown masked except its last 4 characters. */
export function maskValue(value: string) {
  return value.length <= 4 ? '••••' : `••••${value.slice(-4)}`
}

/** Status from the dates: revoked, expired, expiring (within 14 days) or active. */
export function tokenStatusOf(token: { revoked_at: string | null; expires_at: string | null }, now = Date.now()): ApiTokenStatus {
  if (token.revoked_at) return 'revoked'
  if (token.expires_at) {
    const left = Date.parse(token.expires_at) - now
    if (left <= 0) return 'expired'
    if (left <= EXPIRING_DAYS * DAY_MS) return 'expiring'
  }
  return 'active'
}

/** Whether a token's scopes allow a method on an endpoint (empty lists allow all). */
export function scopeAllows(scopes: ApiTokenScopes, target: { endpoint_id: string; service_id: string; method: ApiMethod }) {
  const service = !scopes.services.length || scopes.services.includes(target.service_id)
  const endpoint = !scopes.endpoints.length || scopes.endpoints.includes(target.endpoint_id)
  const method = !scopes.methods.length || scopes.methods.includes(target.method)
  return service && endpoint && method
}

/** Problems with a required header's name: `required`, `pattern` or `reserved` (set by Formalie itself). */
export function checkHeaderName(name: string): 'required' | 'pattern' | 'reserved' | null {
  if (!name) return 'required'
  if (!HEADER_NAME_PATTERN.test(name)) return 'pattern'
  const lower = name.toLowerCase()
  if (RESERVED_HEADERS.includes(lower) || lower.startsWith('formalie-') || lower.startsWith('x-formalie-')) return 'reserved'
  return null
}

/** Problems with a required header's value: `required` or `chars` (printable ASCII only, up to 200). */
export function checkHeaderValue(value: string): 'required' | 'chars' | null {
  if (!value) return 'required'
  return /^[\x21-\x7e][\x20-\x7e]{0,199}$/.test(value) ? null : 'chars'
}

const DAY_MS = 86_400_000
/** "Expiring" shows this many days before a token expires. */
export const EXPIRING_DAYS = 14
/** Expiry choices for a new token, in days (null = never). */
export const TOKEN_EXPIRY_DAYS: (number | null)[] = [30, 90, 365, null]
/** Minutes a short-lived token (client credentials) lasts. */
export const TOKEN_LIFETIMES: number[] = [5, 15, 30, 60]
/** After rotating, the old secret keeps working for this many hours (0 = stops at once). */
export const ROTATION_GRACE_HOURS: number[] = [0, 24, 168]
/** At most this many required headers per endpoint. */
export const MAX_REQUIRED_HEADERS = 5
export const HEADER_NAME_PATTERN = /^[A-Za-z][A-Za-z0-9-]{1,63}$/
/** Set by HTTP or by Formalie itself; never a custom required header. */
export const RESERVED_HEADERS: string[] = ['authorization', 'content-type', 'content-length', 'host', 'cookie', 'formalie-key', 'accept', 'user-agent', 'origin', 'referer']

/**
 * A Formalie-Key (owner, 2026-10-06): required on POST, optional on GET, PUT and DELETE (checked when
 * sent). 16 to 100 letters, digits and . _ : -, and not an obvious pattern: a key reused by mistake
 * would make every later POST answer with the first record, so `1111…`, `abab…` and counting
 * (`1234567890…`) are refused. A UUID always passes.
 */
export const CALL_KEY_MIN = 16
export function checkCallKey(key: string): 'missing' | 'invalid' | 'short' | 'weak' | null {
  if (!key) return 'missing'
  if (key.length > 100 || !/^[A-Za-z0-9._:-]+$/.test(key)) return 'invalid'
  if (key.length < CALL_KEY_MIN) return 'short'
  const plain = key.toLowerCase().replace(/[._:-]/g, '')
  if (new Set(plain).size <= 4) return 'weak'
  let up = 0
  let down = 0
  for (let i = 1; i < plain.length; i++) {
    const step = plain.charCodeAt(i) - plain.charCodeAt(i - 1)
    if (step === 1) up++
    if (step === -1) down++
  }
  return Math.max(up, down) >= (plain.length - 1) * 0.75 ? 'weak' : null
}

/** The same JSON whatever the order of its keys, so a retry is recognised as the same request. */
export function canonicalJson(value: unknown): string {
  if (Array.isArray(value)) return `[${value.map(canonicalJson).join(',')}]`
  if (value && typeof value === 'object') return `{${Object.keys(value).sort().map(key => `${JSON.stringify(key)}:${canonicalJson((value as Record<string, unknown>)[key])}`).join(',')}}`
  return JSON.stringify(value ?? null)
}

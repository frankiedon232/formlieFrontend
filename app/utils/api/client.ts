/**
 * Framework-free API client implementing the browser half of docs/SECURITY-PROTOCOL.md.
 * `useApi()` wraps it with Nuxt bits (base URL, session token, real fetch); tests drive it
 * with a fake server. All state (session key, CSRF token) lives in this closure — memory
 * only, never storage (CLAUDE.md rule 12).
 */
import type { ApiResponse, ApiSuccess, CsrfTokenResponse } from '#shared/types/api'
import type { Envelope, EnvelopeRequestPayload, HandshakeResponse } from '#shared/types/crypto'
import {
  ENVELOPE_CONTENT_TYPE,
  ENVELOPE_HEADER,
  deriveSessionKey,
  encodeEnvelopeHeader,
  exportRawPublicKey,
  generateEcdhKeyPair,
  isEnvelope,
  isEnvelopeFresh,
  openEnvelope,
  sealEnvelope,
} from '#shared/utils/crypto/envelope'
import { ABORTED_ERROR, ApiError, BAD_RESPONSE_ERROR, NETWORK_ERROR } from './errors'

export type HttpMethod = 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE'

export interface TransportRequest {
  method: HttpMethod
  headers: Record<string, string>
  body?: string
  signal?: AbortSignal
}

export interface TransportResponse {
  status: number
  json: unknown
}

export type Transport = (url: string, init: TransportRequest) => Promise<TransportResponse>

export interface ApiClientOptions {
  /** e.g. `/api/v1` or `https://api.formalie.com/api/v1` */
  baseUrl: string
  transport: Transport
  getAccessToken: () => string | null
  /** Extra headers on every request (e.g. the dev-only tenant override). */
  getExtraHeaders?: () => Record<string, string>
  /** Exchange the refresh cookie for a new access token. Resolves true on success. */
  refreshAccessToken?: () => Promise<boolean>
  /** Called when the session can't be recovered (refresh failed / revoked). */
  onUnauthenticated?: (error: ApiError) => void
  /** Re-handshake this long before the key's expiry. */
  keyExpiryBufferMs?: number
}

export interface RequestOptions {
  query?: Record<string, unknown>
  body?: unknown
  signal?: AbortSignal
  /** Internal: used by the refresh call itself so it can't loop. */
  skipAuthRefresh?: boolean
}

interface SecureSession {
  kid: string
  key: CryptoKey
  expiresAt: number
}

const STATE_CHANGING = new Set<HttpMethod>(['POST', 'PUT', 'PATCH', 'DELETE'])
const CSRF_EXPIRY_BUFFER_MS = 60_000

function pathOf(baseUrl: string): string {
  return /^https?:\/\//.test(baseUrl)
    ? new URL(baseUrl).pathname.replace(/\/$/, '')
    : baseUrl.replace(/\/$/, '')
}

function toApiError(body: ApiResponse, status: number): ApiError {
  if (!body.success) {
    const { code, message, trace_id, details } = body.error
    return new ApiError(code, message, status, trace_id, details ?? [])
  }
  return new ApiError(BAD_RESPONSE_ERROR, 'Unexpected response.', status)
}

export function createApiClient(options: ApiClientOptions) {
  const basePath = pathOf(options.baseUrl)
  const bufferMs = options.keyExpiryBufferMs ?? 30_000

  let session: SecureSession | null = null
  let pendingHandshake: Promise<SecureSession> | null = null
  let csrf: { token: string; expiresAt: number; kid: string } | null = null
  let pendingCsrf: Promise<string> | null = null
  let pendingRefresh: Promise<boolean> | null = null

  async function send(url: string, init: TransportRequest): Promise<TransportResponse> {
    try {
      return await options.transport(url, init)
    } catch (error) {
      if (init.signal?.aborted || (error as Error)?.name === 'AbortError') {
        throw new ApiError(ABORTED_ERROR, 'Request cancelled.')
      }
      throw new ApiError(NETWORK_ERROR, "Can't reach the server.")
    }
  }

  async function handshake(): Promise<SecureSession> {
    const keys = await generateEcdhKeyPair()
    const response = await send(`${options.baseUrl}/crypto/handshake`, {
      method: 'POST',
      headers: {
        ...options.getExtraHeaders?.(),
        'content-type': 'application/json',
        accept: 'application/json',
      },
      body: JSON.stringify({
        client_public_key: await exportRawPublicKey(keys.publicKey),
        client_ts: Date.now(),
      }),
    })
    const body = response.json as ApiResponse<HandshakeResponse>
    if (!body || typeof body !== 'object' || !('success' in body)) {
      throw new ApiError(BAD_RESPONSE_ERROR, 'Unexpected handshake response.', response.status)
    }
    if (!body.success) throw toApiError(body, response.status)
    const { key_id, server_public_key, salt, expires_at } = body.data
    return {
      kid: key_id,
      key: await deriveSessionKey(keys.privateKey, server_public_key, salt),
      expiresAt: Date.parse(expires_at),
    }
  }

  /** Secure session key, created on first use and renewed shortly before it expires. */
  async function ensureSession(): Promise<SecureSession> {
    if (session && session.expiresAt - bufferMs > Date.now()) return session
    pendingHandshake ??= handshake().finally(() => {
      pendingHandshake = null
    })
    session = await pendingHandshake
    return session
  }

  function resetSecureSession() {
    session = null
    csrf = null
  }

  async function ensureCsrf(signal?: AbortSignal): Promise<string> {
    const current = await ensureSession()
    if (csrf && csrf.kid === current.kid && csrf.expiresAt - CSRF_EXPIRY_BUFFER_MS > Date.now())
      return csrf.token
    pendingCsrf ??= request<CsrfTokenResponse>('GET', '/auth/csrf', { signal })
      .then(({ data }) => {
        csrf = { token: data.csrf_token, expiresAt: Date.parse(data.expires_at), kid: current.kid }
        return data.csrf_token
      })
      .finally(() => {
        pendingCsrf = null
      })
    return pendingCsrf
  }

  async function refreshOnce(): Promise<boolean> {
    if (!options.refreshAccessToken) return false
    pendingRefresh ??= options.refreshAccessToken().finally(() => {
      pendingRefresh = null
    })
    return pendingRefresh
  }

  async function attempt<T>(method: HttpMethod, path: string, opts: RequestOptions): Promise<ApiSuccess<T>> {
    // CSRF first: fetching it may re-handshake, and the envelope must be sealed with the final key.
    const csrfToken = STATE_CHANGING.has(method) ? await ensureCsrf(opts.signal) : null
    const secure = await ensureSession()
    const payload: EnvelopeRequestPayload = {
      method,
      path: `${basePath}${path}`,
      query: opts.query ?? {},
      body: opts.body ?? null,
    }
    const envelope = await sealEnvelope(secure.key, secure.kid, payload)
    const headers: Record<string, string> = {
      ...options.getExtraHeaders?.(),
      accept: `${ENVELOPE_CONTENT_TYPE}, application/json`,
    }

    const token = options.getAccessToken()
    if (token) headers.authorization = `Bearer ${token}`
    if (csrfToken) headers['x-csrf-token'] = csrfToken

    let body: string | undefined
    if (method === 'GET' || method === 'DELETE') {
      headers[ENVELOPE_HEADER.toLowerCase()] = encodeEnvelopeHeader(envelope)
    } else {
      headers['content-type'] = ENVELOPE_CONTENT_TYPE
      body = JSON.stringify(envelope)
    }

    const response = await send(`${options.baseUrl}${path}`, { method, headers, body, signal: opts.signal })
    return decode<T>(response, secure)
  }

  async function decode<T>(response: TransportResponse, secure: SecureSession): Promise<ApiSuccess<T>> {
    let body: ApiResponse<T>
    if (isEnvelope(response.json)) {
      const envelope = response.json as Envelope
      if (envelope.kid !== secure.kid || !isEnvelopeFresh(envelope)) {
        throw new ApiError('FRM-SEC-1005', 'Request integrity check failed.', response.status)
      }
      try {
        body = await openEnvelope<ApiResponse<T>>(secure.key, envelope)
      } catch {
        throw new ApiError('FRM-SEC-1005', 'Request integrity check failed.', response.status)
      }
    } else if (response.json && typeof response.json === 'object' && 'success' in response.json) {
      // Only errors the server can't encrypt (unknown key) arrive in plaintext.
      body = response.json as ApiResponse<T>
      if (body.success) throw new ApiError('FRM-SEC-1001', 'Secure channel required.', response.status)
    } else {
      throw new ApiError(BAD_RESPONSE_ERROR, 'Unexpected response.', response.status)
    }
    if (body.success) return body
    throw toApiError(body, response.status)
  }

  /**
   * One enveloped request. Recovers transparently, once each:
   * FRM-SEC-1004 → re-handshake · FRM-SEC-1006 → new CSRF token · FRM-SEC-1002 → resend ·
   * FRM-AUTH-1001 → refresh access token. Anything else throws ApiError.
   */
  async function request<T>(
    method: HttpMethod,
    path: string,
    opts: RequestOptions = {},
  ): Promise<ApiSuccess<T>> {
    const recovered = new Set<string>()
    for (;;) {
      try {
        return await attempt<T>(method, path, opts)
      } catch (error) {
        if (!(error instanceof ApiError) || recovered.has(error.code)) throw error
        recovered.add(error.code)
        if (error.code === 'FRM-SEC-1004') {
          resetSecureSession()
        } else if (error.code === 'FRM-SEC-1006') {
          csrf = null
        } else if (error.code === 'FRM-SEC-1002') {
          // clock skew or slow network: a fresh envelope usually passes
        } else if (error.code === 'FRM-AUTH-1001' && !opts.skipAuthRefresh) {
          if (!(await refreshOnce())) {
            options.onUnauthenticated?.(error)
            throw error
          }
        } else {
          if (['FRM-AUTH-1010', 'FRM-AUTH-1011', 'FRM-AUTH-1012'].includes(error.code)) {
            options.onUnauthenticated?.(error)
          }
          throw error
        }
      }
    }
  }

  return { request, resetSecureSession }
}

export type ApiClient = ReturnType<typeof createApiClient>

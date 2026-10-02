import { beforeEach, describe, expect, it } from 'vitest'
import type { ApiResponse } from '../../shared/types/api'
import type { EnvelopeRequestPayload } from '../../shared/types/crypto'
import { bytesToBase64, randomBytes } from '../../shared/utils/crypto/encoding'
import {
  ENVELOPE_CONTENT_TYPE,
  decodeEnvelopeHeader,
  deriveSessionKey,
  exportRawPublicKey,
  generateEcdhKeyPair,
  isEnvelope,
  openEnvelope,
  sealEnvelope,
} from '../../shared/utils/crypto/envelope'
import { createApiClient, type Transport } from '../../app/utils/api/client'
import { ApiError } from '../../app/utils/api/errors'

/** Minimal server speaking SECURITY-PROTOCOL.md, with switches to simulate failures. */
function createFakeServer() {
  const keys = new Map<string, CryptoKey>()
  const nonces = new Set<string>()
  const csrfTokens = new Map<string, string>() // token → kid
  const calls: string[] = []
  const flags = { expireKeys: false, expireCsrf: false, expireToken: false, refreshWorks: true }
  let validToken = 'token-1'

  const fail = (code: string, _status: number): ApiResponse => ({
    success: false,
    error: { code, message: code, trace_id: 'trace-' + code, details: [] },
  })

  const transport: Transport = async (url, init) => {
    const path = new URL(url, 'https://test.formalie.dev').pathname
    if (init.signal?.aborted) throw Object.assign(new Error('aborted'), { name: 'AbortError' })

    if (path === '/api/v1/crypto/handshake') {
      calls.push('handshake')
      const { client_public_key } = JSON.parse(init.body!)
      const server = await generateEcdhKeyPair()
      const salt = bytesToBase64(randomBytes(32))
      const kid = `kid-${keys.size + 1}`
      keys.set(kid, await deriveSessionKey(server.privateKey, client_public_key, salt))
      return {
        status: 200,
        json: {
          success: true,
          meta: {},
          data: {
            key_id: kid,
            server_public_key: await exportRawPublicKey(server.publicKey),
            salt,
            expires_at: new Date(Date.now() + 30 * 60_000).toISOString(),
          },
        },
      }
    }

    const envelope =
      init.method === 'GET' || init.method === 'DELETE'
        ? decodeEnvelopeHeader(init.headers['x-formalie-envelope'] ?? '')
        : init.headers['content-type'] === ENVELOPE_CONTENT_TYPE
          ? JSON.parse(init.body!)
          : null
    if (!isEnvelope(envelope)) return { status: 400, json: fail('FRM-SEC-1001', 400) }

    if (flags.expireKeys) {
      flags.expireKeys = false
      keys.clear()
    }
    const key = keys.get(envelope.kid)
    if (!key) return { status: 401, json: fail('FRM-SEC-1004', 401) }
    const reply = async (status: number, body: ApiResponse) => ({
      status,
      json: await sealEnvelope(key, envelope.kid, body),
    })
    if (nonces.has(envelope.nonce)) return reply(400, fail('FRM-SEC-1003', 400))
    nonces.add(envelope.nonce)

    const payload = await openEnvelope<EnvelopeRequestPayload>(key, envelope).catch(() => null)
    if (!payload) return reply(400, fail('FRM-SEC-1005', 400))
    if (payload.path !== path || payload.method !== init.method) return reply(400, fail('FRM-SEC-1005', 400))
    calls.push(`${init.method} ${path}`)

    if (path === '/api/v1/auth/csrf') {
      const token = `csrf-${csrfTokens.size + 1}`
      csrfTokens.set(token, envelope.kid)
      return reply(200, {
        success: true,
        meta: {},
        data: { csrf_token: token, expires_at: new Date(Date.now() + 7_200_000).toISOString() },
      })
    }

    if (init.method !== 'GET' && init.method !== 'DELETE') {
      if (flags.expireCsrf) {
        flags.expireCsrf = false
        csrfTokens.clear()
      }
      if (csrfTokens.get(init.headers['x-csrf-token'] ?? '') !== envelope.kid) {
        return reply(403, fail('FRM-SEC-1006', 403))
      }
    }

    if (path === '/api/v1/auth/refresh') {
      if (!flags.refreshWorks) return reply(401, fail('FRM-AUTH-1012', 401))
      validToken = 'token-2'
      return reply(200, { success: true, meta: {}, data: { access_token: validToken } })
    }

    if (path === '/api/v1/private') {
      if (flags.expireToken) {
        flags.expireToken = false
        return reply(401, fail('FRM-AUTH-1001', 401))
      }
      if (init.headers.authorization !== `Bearer ${validToken}`) return reply(401, fail('FRM-AUTH-1010', 401))
    }

    if (path === '/api/v1/missing') return reply(404, fail('FRM-GEN-1004', 404))

    return reply(200, { success: true, meta: {}, data: { query: payload.query, body: payload.body } })
  }

  return { transport, calls, flags, getValidToken: () => validToken }
}

describe('api client', () => {
  let server: ReturnType<typeof createFakeServer>
  let token: string | null
  let unauthenticated: ApiError | null
  let client: ReturnType<typeof createApiClient>

  beforeEach(() => {
    server = createFakeServer()
    token = 'token-1'
    unauthenticated = null
    client = createApiClient({
      baseUrl: '/api/v1',
      transport: server.transport,
      getAccessToken: () => token,
      refreshAccessToken: async () => {
        try {
          const { data } = await client.request<{ access_token: string }>('POST', '/auth/refresh', {
            skipAuthRefresh: true,
          })
          token = data.access_token
          return true
        } catch {
          return false
        }
      },
      onUnauthenticated: error => {
        unauthenticated = error
      },
    })
  })

  it('handshakes once and sends query inside the envelope (GET)', async () => {
    const a = await client.request<{ query: unknown }>('GET', '/echo', { query: { page: 2, q: 'ünï' } })
    await client.request('GET', '/echo')
    expect(a.data.query).toEqual({ page: 2, q: 'ünï' })
    expect(server.calls.filter(c => c === 'handshake')).toHaveLength(1)
  })

  it('fetches a CSRF token for state-changing requests and reuses it', async () => {
    const res = await client.request<{ body: unknown }>('POST', '/echo', { body: { name: 'Form' } })
    await client.request('PATCH', '/echo', { body: { name: 'Renamed' } })
    expect(res.data.body).toEqual({ name: 'Form' })
    expect(server.calls.filter(c => c === 'GET /api/v1/auth/csrf')).toHaveLength(1)
  })

  it('re-handshakes transparently on FRM-SEC-1004 (key expired / server restart)', async () => {
    await client.request('GET', '/echo')
    server.flags.expireKeys = true
    await expect(client.request('POST', '/echo', { body: {} })).resolves.toMatchObject({ success: true })
    expect(server.calls.filter(c => c === 'handshake')).toHaveLength(2)
  })

  it('renews the CSRF token on FRM-SEC-1006', async () => {
    await client.request('POST', '/echo', { body: {} })
    server.flags.expireCsrf = true
    await expect(client.request('POST', '/echo', { body: {} })).resolves.toMatchObject({ success: true })
    expect(server.calls.filter(c => c === 'GET /api/v1/auth/csrf')).toHaveLength(2)
  })

  it('refreshes the access token once on FRM-AUTH-1001 and retries', async () => {
    server.flags.expireToken = true
    await expect(client.request('GET', '/private')).resolves.toMatchObject({ success: true })
    expect(token).toBe('token-2')
  })

  it('reports unauthenticated when refresh fails', async () => {
    server.flags.expireToken = true
    server.flags.refreshWorks = false
    await expect(client.request('GET', '/private')).rejects.toMatchObject({ code: 'FRM-AUTH-1001' })
    expect(unauthenticated?.code).toBe('FRM-AUTH-1001')
  })

  it('throws ApiError with code, status and trace id for server errors', async () => {
    const error = await client.request('GET', '/missing').catch(e => e)
    expect(error).toBeInstanceOf(ApiError)
    expect(error).toMatchObject({ code: 'FRM-GEN-1004', status: 404, traceId: 'trace-FRM-GEN-1004' })
  })

  it('maps aborts and network failures to client codes', async () => {
    const controller = new AbortController()
    controller.abort()
    await expect(client.request('GET', '/echo', { signal: controller.signal })).rejects.toMatchObject({
      code: 'FRM-NET-1001',
      aborted: true,
    })
    const offline = createApiClient({
      baseUrl: '/api/v1',
      transport: async () => {
        throw new TypeError('Failed to fetch')
      },
      getAccessToken: () => null,
    })
    await expect(offline.request('GET', '/echo')).rejects.toMatchObject({ code: 'FRM-NET-1000' })
  })
})

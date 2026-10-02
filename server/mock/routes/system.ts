import { z } from 'zod'
import type { CsrfTokenResponse, HealthResponse } from '#shared/types/api'
import type { HandshakeResponse } from '#shared/types/crypto'
import { bytesToBase64, randomBytes } from '#shared/utils/crypto/encoding'
import { deriveSessionKey, exportRawPublicKey, generateEcdhKeyPair } from '#shared/utils/crypto/envelope'
import { defineMockRoute } from '../core/route'
import { MockError, ok } from '../core/respond'
import { issueCsrfToken, saveSessionKey } from '../core/store'

const handshakeSchema = z.object({
  client_public_key: z.string().min(80).max(120),
  client_ts: z.number().int(),
})

export const health = defineMockRoute(
  () => ok<HealthResponse>({ status: 'ok', mock: true, time: new Date().toISOString() }),
  { plain: true },
)

/** POST /crypto/handshake — ECDH P-256 + HKDF, the only plaintext JSON endpoint. */
export const handshake = defineMockRoute(
  async ({ event, body }) => {
    const parsed = handshakeSchema.safeParse(body)
    if (!parsed.success) {
      throw new MockError(
        'FRM-GEN-1002',
        parsed.error.issues.map(issue => ({
          field: issue.path.join('.'),
          message: issue.message,
        })),
      )
    }

    const serverKeys = await generateEcdhKeyPair()
    const salt = bytesToBase64(randomBytes(32))
    const key = await deriveSessionKey(serverKeys.privateKey, parsed.data.client_public_key, salt).catch(
      () => {
        throw new MockError('FRM-GEN-1001', [
          { field: 'client_public_key', message: 'Invalid P-256 public key.' },
        ])
      },
    )

    const kid = crypto.randomUUID()
    const tenantHost = getRequestHost(event, { xForwardedHost: true })
    const expiresAt = saveSessionKey(kid, key, tenantHost)

    return ok<HandshakeResponse>({
      key_id: kid,
      server_public_key: await exportRawPublicKey(serverKeys.publicKey),
      salt,
      expires_at: expiresAt.toISOString(),
    })
  },
  { plain: true },
)

/** GET /auth/csrf — pre-session CSRF token bound to the handshake key. */
export const csrf = defineMockRoute(({ kid }) => {
  const { token, expiresAt } = issueCsrfToken(kid)
  return ok<CsrfTokenResponse>({ csrf_token: token, expires_at: expiresAt.toISOString() })
})

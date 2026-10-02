import { describe, expect, it } from 'vitest'
import { bytesToBase64, randomBytes } from '../../shared/utils/crypto/encoding'
import {
  decodeEnvelopeHeader,
  deriveSessionKey,
  encodeEnvelopeHeader,
  exportRawPublicKey,
  generateEcdhKeyPair,
  isEnvelopeFresh,
  openEnvelope,
  sealEnvelope,
} from '../../shared/utils/crypto/envelope'

async function handshake() {
  const client = await generateEcdhKeyPair()
  const server = await generateEcdhKeyPair()
  const salt = bytesToBase64(randomBytes(32))
  const clientKey = await deriveSessionKey(
    client.privateKey,
    await exportRawPublicKey(server.publicKey),
    salt,
  )
  const serverKey = await deriveSessionKey(
    server.privateKey,
    await exportRawPublicKey(client.publicKey),
    salt,
  )
  return { clientKey, serverKey }
}

describe('envelope', () => {
  it('both sides derive the same key and round-trip a payload', async () => {
    const { clientKey, serverKey } = await handshake()
    const payload = { method: 'POST', path: '/api/v1/forms', query: {}, body: { name: 'Ünïcødé ✓' } }
    const envelope = await sealEnvelope(clientKey, 'kid-1', payload)
    expect(await openEnvelope(serverKey, envelope)).toEqual(payload)
  })

  it('rejects a tampered nonce (AAD mismatch)', async () => {
    const { clientKey, serverKey } = await handshake()
    const envelope = await sealEnvelope(clientKey, 'kid-1', { ok: true })
    await expect(
      openEnvelope(serverKey, { ...envelope, nonce: bytesToBase64(randomBytes(16)) }),
    ).rejects.toThrow()
  })

  it('rejects a different session key', async () => {
    const first = await handshake()
    const second = await handshake()
    const envelope = await sealEnvelope(first.clientKey, 'kid-1', { ok: true })
    await expect(openEnvelope(second.serverKey, envelope)).rejects.toThrow()
  })

  it('encodes and decodes the GET header form', async () => {
    const { clientKey } = await handshake()
    const envelope = await sealEnvelope(clientKey, 'kid-1', { ok: true })
    const header = encodeEnvelopeHeader(envelope)
    expect(header).toMatch(/^[\w-]+$/)
    expect(decodeEnvelopeHeader(header)).toEqual(envelope)
    expect(decodeEnvelopeHeader('not-an-envelope')).toBeNull()
  })

  it('enforces the 60 s freshness window', () => {
    const now = Date.now()
    expect(isEnvelopeFresh({ ts: now - 59_000 }, now)).toBe(true)
    expect(isEnvelopeFresh({ ts: now - 61_000 }, now)).toBe(false)
  })
})

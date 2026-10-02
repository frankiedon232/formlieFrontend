/**
 * App-layer encryption envelope (docs/SECURITY-PROTOCOL.md).
 * Pure WebCrypto: shared by the browser (useCrypto) and the Nitro mock API,
 * so both sides are guaranteed to speak the same protocol.
 *
 * ECDH P-256 → HKDF-SHA256 (info = formalie-envelope-v1) → AES-256-GCM.
 * AAD = `${kid}|${ts}|${nonce}`.
 */
import type { Envelope } from '../../types/crypto'
import {
  base64ToBase64Url,
  base64ToBytes,
  base64UrlToBase64,
  bytesToBase64,
  randomBytes,
  utf8Decode,
  utf8Encode,
} from './encoding'

export const ENVELOPE_HKDF_INFO = 'formalie-envelope-v1'
export const ENVELOPE_HEADER = 'X-Formalie-Envelope'
export const ENVELOPE_CONTENT_TYPE = 'application/vnd.formalie.enc+json'
export const ENVELOPE_MAX_SKEW_MS = 60_000
export const ENVELOPE_NONCE_TTL_S = 120

const ECDH_PARAMS: EcKeyGenParams = { name: 'ECDH', namedCurve: 'P-256' }

export function generateEcdhKeyPair(): Promise<CryptoKeyPair> {
  return crypto.subtle.generateKey(ECDH_PARAMS, false, ['deriveBits'])
}

export async function exportRawPublicKey(key: CryptoKey): Promise<string> {
  return bytesToBase64(await crypto.subtle.exportKey('raw', key))
}

export function importRawPublicKey(base64: string): Promise<CryptoKey> {
  return crypto.subtle.importKey('raw', base64ToBytes(base64), ECDH_PARAMS, false, [])
}

/** Derives the 256-bit AES-GCM session key from our private key and the peer's public key. */
export async function deriveSessionKey(
  privateKey: CryptoKey,
  peerPublicKeyBase64: string,
  saltBase64: string,
): Promise<CryptoKey> {
  const peerPublicKey = await importRawPublicKey(peerPublicKeyBase64)
  const sharedBits = await crypto.subtle.deriveBits({ name: 'ECDH', public: peerPublicKey }, privateKey, 256)
  const hkdfKey = await crypto.subtle.importKey('raw', sharedBits, 'HKDF', false, ['deriveKey'])
  return crypto.subtle.deriveKey(
    {
      name: 'HKDF',
      hash: 'SHA-256',
      salt: base64ToBytes(saltBase64),
      info: utf8Encode(ENVELOPE_HKDF_INFO),
    },
    hkdfKey,
    { name: 'AES-GCM', length: 256 },
    false,
    ['encrypt', 'decrypt'],
  )
}

function envelopeAad(kid: string, ts: number, nonce: string): Uint8Array<ArrayBuffer> {
  return utf8Encode(`${kid}|${ts}|${nonce}`)
}

/** Encrypts any JSON-serialisable payload into an envelope. */
export async function sealEnvelope(key: CryptoKey, kid: string, payload: unknown): Promise<Envelope> {
  const iv = randomBytes(12)
  const nonce = bytesToBase64(randomBytes(16))
  const ts = Date.now()
  const ciphertext = await crypto.subtle.encrypt(
    { name: 'AES-GCM', iv, additionalData: envelopeAad(kid, ts, nonce) },
    key,
    utf8Encode(JSON.stringify(payload)),
  )
  return { kid, iv: bytesToBase64(iv), ts, nonce, ct: bytesToBase64(ciphertext) }
}

/** Decrypts an envelope. Throws if the key, AAD or ciphertext do not match. */
export async function openEnvelope<T = unknown>(key: CryptoKey, envelope: Envelope): Promise<T> {
  const plaintext = await crypto.subtle.decrypt(
    {
      name: 'AES-GCM',
      iv: base64ToBytes(envelope.iv),
      additionalData: envelopeAad(envelope.kid, envelope.ts, envelope.nonce),
    },
    key,
    base64ToBytes(envelope.ct),
  )
  return JSON.parse(utf8Decode(plaintext)) as T
}

export function isEnvelopeFresh(envelope: Pick<Envelope, 'ts'>, now = Date.now()): boolean {
  return Math.abs(now - envelope.ts) <= ENVELOPE_MAX_SKEW_MS
}

export function isEnvelope(value: unknown): value is Envelope {
  if (!value || typeof value !== 'object') return false
  const v = value as Record<string, unknown>
  return (
    typeof v.kid === 'string' &&
    typeof v.iv === 'string' &&
    typeof v.ts === 'number' &&
    typeof v.nonce === 'string' &&
    typeof v.ct === 'string'
  )
}

/** GET/DELETE: the envelope travels in a header as base64url JSON. */
export function encodeEnvelopeHeader(envelope: Envelope): string {
  return base64ToBase64Url(bytesToBase64(utf8Encode(JSON.stringify(envelope))))
}

export function decodeEnvelopeHeader(value: string): Envelope | null {
  try {
    const parsed: unknown = JSON.parse(utf8Decode(base64ToBytes(base64UrlToBase64(value))))
    return isEnvelope(parsed) ? parsed : null
  } catch {
    return null
  }
}

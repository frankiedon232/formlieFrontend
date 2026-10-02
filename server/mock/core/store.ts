/**
 * In-memory stand-in for Redis: session keys, envelope nonces, CSRF tokens.
 * A dev-server restart wipes it, which conveniently exercises the client's
 * transparent re-handshake on FRM-SEC-1004.
 */
import { ENVELOPE_NONCE_TTL_S } from '#shared/utils/crypto/envelope'

const SESSION_KEY_TTL_MS = 30 * 60 * 1000
const CSRF_TTL_MS = 2 * 60 * 60 * 1000

interface SessionKeyEntry {
  key: CryptoKey
  tenantHost: string
  expiresAt: number
}

interface CsrfEntry {
  kid: string
  expiresAt: number
}

const sessionKeys = new Map<string, SessionKeyEntry>()
const seenNonces = new Map<string, number>()
const csrfTokens = new Map<string, CsrfEntry>()

function purgeExpired<T>(map: Map<string, T>, expiry: (value: T) => number) {
  const now = Date.now()
  for (const [id, value] of map) if (expiry(value) <= now) map.delete(id)
}

export function saveSessionKey(kid: string, key: CryptoKey, tenantHost: string): Date {
  purgeExpired(sessionKeys, entry => entry.expiresAt)
  const expiresAt = Date.now() + SESSION_KEY_TTL_MS
  sessionKeys.set(kid, { key, tenantHost, expiresAt })
  return new Date(expiresAt)
}

/** Returns the key and slides its expiry, or null when unknown/expired. */
export function useSessionKey(kid: string): SessionKeyEntry | null {
  const entry = sessionKeys.get(kid)
  if (!entry || entry.expiresAt <= Date.now()) {
    sessionKeys.delete(kid)
    return null
  }
  entry.expiresAt = Date.now() + SESSION_KEY_TTL_MS
  return entry
}

/** Equivalent of Redis `SET NX EX 120`: true the first time, false on replay. */
export function claimNonce(nonce: string): boolean {
  purgeExpired(seenNonces, expiresAt => expiresAt)
  if (seenNonces.has(nonce)) return false
  seenNonces.set(nonce, Date.now() + ENVELOPE_NONCE_TTL_S * 1000)
  return true
}

export function issueCsrfToken(kid: string): { token: string; expiresAt: Date } {
  purgeExpired(csrfTokens, entry => entry.expiresAt)
  const token = crypto.randomUUID().replace(/-/g, '') + crypto.randomUUID().replace(/-/g, '')
  const expiresAt = Date.now() + CSRF_TTL_MS
  csrfTokens.set(token, { kid, expiresAt })
  return { token, expiresAt: new Date(expiresAt) }
}

export function isCsrfTokenValid(token: string | undefined, kid: string): boolean {
  if (!token) return false
  const entry = csrfTokens.get(token)
  return !!entry && entry.kid === kid && entry.expiresAt > Date.now()
}

/**
 * Encrypted references (owner, 2026-10-03; SECURITY-PROTOCOL §10): the API never hands a real
 * record id to the browser. Every id leaves as an encrypted reference and comes back in as one;
 * only the server holds the key.
 *
 *   ref = base64url( AES-256(id block) ‖ HMAC-SHA256(ct)[0..3] )   → 27 URL-safe characters
 *
 *   - AES-256 on one 16-byte block is a keyed permutation: the same id always gives the same ref
 *     (bookmarks keep working), refs reveal nothing about the id, and without the key nobody can
 *     produce a ref for another record.
 *   - The 4-byte tag rejects typed-in or altered refs before any lookup.
 *   - Id blocks: a UUID's 16 bytes, or a workspace template key (`ws_` + 12 hex) in a marked block.
 *
 * The mock applies it centrally (core/route.ts): replies are encoded, route params / query / body
 * decoded, routes and stores keep working with real ids. The real API does the same at its edge.
 */
import { createCipheriv, createDecipheriv, createHmac, randomBytes } from 'node:crypto'
import { loadPersisted, savePersisted } from './persist'

// One key pair per mock install, kept across restarts (production: a managed secret with rotation).
const stored = loadPersisted<{ enc?: string; mac?: string }>('id-keys', {})
if (!stored.enc || !stored.mac) {
  stored.enc = randomBytes(32).toString('base64')
  stored.mac = randomBytes(32).toString('base64')
  savePersisted('id-keys', () => stored)
}
const ENC_KEY = Buffer.from(stored.enc, 'base64')
const MAC_KEY = Buffer.from(stored.mac, 'base64')

const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i
const UUID_IN_TEXT = /[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}/gi
const WS_KEY = /^ws_([0-9a-f]{12})$/
const REF = /^[A-Za-z0-9_-]{27}$/
const REF_IN_TEXT = /(?<![A-Za-z0-9_-])[A-Za-z0-9_-]{27}(?![A-Za-z0-9_-])/g
// Workspace template keys: 'ws' marker, 8 zero bytes, 6 key bytes (a UUID v4 never looks like this).
const WS_MARK = Buffer.from([0x77, 0x73, 0, 0, 0, 0, 0, 0, 0, 0])

function block(id: string): Buffer | null {
  if (UUID.test(id)) return Buffer.from(id.replace(/-/g, ''), 'hex')
  const ws = WS_KEY.exec(id)
  return ws ? Buffer.concat([WS_MARK, Buffer.from(ws[1]!, 'hex')]) : null
}
function fromBlock(raw: Buffer): string {
  if (raw.subarray(0, 10).equals(WS_MARK)) return `ws_${raw.subarray(10).toString('hex')}`
  const hex = raw.toString('hex')
  return `${hex.slice(0, 8)}-${hex.slice(8, 12)}-${hex.slice(12, 16)}-${hex.slice(16, 20)}-${hex.slice(20)}`
}
const tag = (ct: Buffer) => createHmac('sha256', MAC_KEY).update(ct).digest().subarray(0, 4)

const encodeCache = new Map<string, string>()
const decodeCache = new Map<string, string | null>()

/** The encrypted reference for an id (ids the codec doesn't handle are returned unchanged). */
export function encodeId(id: string): string {
  const hit = encodeCache.get(id)
  if (hit) return hit
  const plain = block(id)
  if (!plain) return id
  const cipher = createCipheriv('aes-256-ecb', ENC_KEY, null).setAutoPadding(false)
  const ct = Buffer.concat([cipher.update(plain), cipher.final()])
  const ref = Buffer.concat([ct, tag(ct)]).toString('base64url')
  encodeCache.set(id, ref)
  decodeCache.set(ref, id)
  return ref
}

/** The id behind a reference, or null when it isn't a valid one (wrong tag, typed-in, altered). */
export function decodeId(ref: string): string | null {
  if (decodeCache.has(ref)) return decodeCache.get(ref)!
  if (!REF.test(ref)) return null
  const raw = Buffer.from(ref, 'base64url')
  const ct = raw.subarray(0, 16)
  if (raw.length !== 20 || !tag(ct).equals(raw.subarray(16))) return null
  const decipher = createDecipheriv('aes-256-ecb', ENC_KEY, null).setAutoPadding(false)
  const id = fromBlock(Buffer.concat([decipher.update(ct), decipher.final()]))
  if (decodeCache.size > 50_000) decodeCache.clear()
  decodeCache.set(ref, id)
  return id
}

/** Every id in a reply → its reference (also ids inside text such as `/api/v1/files/{id}`). */
export function encodeIds<T>(value: T): T {
  if (typeof value === 'string') {
    if (UUID.test(value) || WS_KEY.test(value)) return encodeId(value) as T
    return (value.length > 36 ? value.replace(UUID_IN_TEXT, encodeId) : value) as T
  }
  if (Array.isArray(value)) return value.map(encodeIds) as T
  if (value && typeof value === 'object') {
    const out: Record<string, unknown> = {}
    for (const [key, item] of Object.entries(value)) out[key] = encodeIds(item)
    return out as T
  }
  return value
}

/** Every reference in a request → the real id (anything else stays as it is). */
export function decodeIds<T>(value: T): T {
  if (typeof value === 'string') {
    if (REF.test(value)) return (decodeId(value) ?? value) as T
    return (value.length > 27 ? value.replace(REF_IN_TEXT, ref => decodeId(ref) ?? ref) : value) as T
  }
  if (Array.isArray(value)) return value.map(decodeIds) as T
  if (value && typeof value === 'object') {
    const out: Record<string, unknown> = {}
    for (const [key, item] of Object.entries(value)) out[key] = decodeIds(item)
    return out as T
  }
  return value
}

/** Route params (`/forms/:id`) carry references: swap them for the real ids before the handler runs. */
export function decodeRouteParams(params: Record<string, string> | undefined) {
  if (!params) return
  for (const [key, value] of Object.entries(params)) {
    const raw = decodeURIComponent(value)
    const decoded = decodeId(raw)
    if (decoded) params[key] = decoded
    // A real id typed into the address is never accepted, only references are.
    else if (UUID.test(raw) || WS_KEY.test(raw)) params[key] = 'invalid-reference'
  }
}

/**
 * Authenticator app codes (RFC 6238 TOTP: HMAC-SHA1, 30 s steps, 6 digits), for two-step sign-in
 * (F16 M5). A secret is 20 random bytes in Base32, shown as a QR code (`otpauth://`) and as text; a code
 * from the step before or after still counts (clocks drift). Recovery codes are kept as hashes only.
 */
import { createHash, createHmac, randomBytes, timingSafeEqual } from 'node:crypto'

const ALPHABET = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ234567'

export function newSecret(): string {
  const bytes = randomBytes(20)
  let bits = ''
  for (const byte of bytes) bits += byte.toString(2).padStart(8, '0')
  let out = ''
  for (let i = 0; i + 5 <= bits.length; i += 5) out += ALPHABET[parseInt(bits.slice(i, i + 5), 2)]
  return out
}

function decode(secret: string): Buffer {
  let bits = ''
  for (const char of secret.replace(/=+$/, '').toUpperCase()) {
    const index = ALPHABET.indexOf(char)
    if (index >= 0) bits += index.toString(2).padStart(5, '0')
  }
  const bytes: number[] = []
  for (let i = 0; i + 8 <= bits.length; i += 8) bytes.push(parseInt(bits.slice(i, i + 8), 2))
  return Buffer.from(bytes)
}

/** The code for a 30-second step (now by default). */
export function totpAt(secret: string, step = Math.floor(Date.now() / 30_000)): string {
  const counter = Buffer.alloc(8)
  counter.writeBigUInt64BE(BigInt(step))
  const hmac = createHmac('sha1', decode(secret)).update(counter).digest()
  const offset = hmac[hmac.length - 1]! & 0x0f
  const value = (hmac.readUInt32BE(offset) & 0x7fffffff) % 1_000_000
  return String(value).padStart(6, '0')
}

export function verifyTotp(secret: string, code: string): boolean {
  if (!/^\d{6}$/.test(code)) return false
  const now = Math.floor(Date.now() / 30_000)
  return [now - 1, now, now + 1].some(step => {
    const expected = Buffer.from(totpAt(secret, step))
    return timingSafeEqual(expected, Buffer.from(code))
  })
}

/** `otpauth://totp/Formalie:name@example.org?secret=…&issuer=Formalie` for the QR code. */
export const otpauthUri = (secret: string, account: string, issuer: string) =>
  `otpauth://totp/${encodeURIComponent(`${issuer}:${account}`)}?secret=${secret}&issuer=${encodeURIComponent(issuer)}&algorithm=SHA1&digits=6&period=30`

/** Ten recovery codes like "k7q2-9xmd", shown once; only their hashes are kept. */
export function newRecoveryCodes(): { codes: string[]; hashes: string[] } {
  const codes = Array.from({ length: 10 }, () => {
    const raw = randomBytes(5).toString('hex').slice(0, 8)
    return `${raw.slice(0, 4)}-${raw.slice(4)}`
  })
  return { codes, hashes: codes.map(hashRecovery) }
}
export const hashRecovery = (code: string) => createHash('sha256').update(code.trim().toLowerCase().replace(/\s+/g, '')).digest('hex')

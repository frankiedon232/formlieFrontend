import { describe, expect, it } from 'vitest'
import { hashRecovery, newRecoveryCodes, newSecret, otpauthUri, totpAt, verifyTotp } from '../../server/mock/core/totp'

// RFC 6238 test secret: the ASCII "12345678901234567890" in Base32
const RFC = 'GEZDGNBVGY3TQOJQGEZDGNBVGY3TQOJQ'

describe('authenticator codes (F16 M5)', () => {
  it('match the RFC 6238 test values (last 6 digits)', () => {
    expect(totpAt(RFC, Math.floor(59 / 30))).toBe('287082')
    expect(totpAt(RFC, Math.floor(1111111109 / 30))).toBe('081804')
    expect(totpAt(RFC, Math.floor(2000000000 / 30))).toBe('279037')
  })
  it('accept the code now and one step either side, nothing else', () => {
    const secret = newSecret()
    const now = Math.floor(Date.now() / 30_000)
    expect(secret).toMatch(/^[A-Z2-7]{32}$/)
    expect(verifyTotp(secret, totpAt(secret, now))).toBe(true)
    expect(verifyTotp(secret, totpAt(secret, now - 1))).toBe(true)
    expect(verifyTotp(secret, totpAt(secret, now + 5))).toBe(false)
    expect(verifyTotp(secret, 'abcdef')).toBe(false)
  })
  it('make ten recovery codes kept as hashes, and an otpauth link for the QR code', () => {
    const { codes, hashes } = newRecoveryCodes()
    expect(codes).toHaveLength(10)
    expect(codes[0]).toMatch(/^[a-f0-9]{4}-[a-f0-9]{4}$/)
    expect(hashes[0]).toBe(hashRecovery(codes[0]!.toUpperCase()))
    expect(otpauthUri('ABC', 'a@example.org', 'Formalie')).toBe('otpauth://totp/Formalie%3Aa%40example.org?secret=ABC&issuer=Formalie&algorithm=SHA1&digits=6&period=30')
  })
})

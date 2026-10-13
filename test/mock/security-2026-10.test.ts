import { readFileSync, readdirSync } from 'node:fs'
import { join } from 'node:path'
import { describe, expect, it } from 'vitest'
import { signedHeaders, webhookSignature } from '../../server/mock/core/webhookSignature'
import { CODES_PER_ADDRESS_PER_DAY, RECEIPTS_PER_ADDRESS_PER_DAY, underDailyCap } from '../../server/mock/core/dailyCap'
import { UNSUBSCRIBE_KINDS, UNSUBSCRIBE_TOKEN_MAX } from '../../shared/types/emails'
import * as crypto from 'node:crypto'

describe('signed webhook deliveries (security review M16)', () => {
  it('signs "{timestamp}.{raw body}" with the token, as the backend does', () => {
    // Worked out separately (Python hmac) so the mock and receivers agree
    expect(webhookSignature('formalie_hook_live_test', 1767225600, '{"id":"evt_1"}')).toBe('v1=f5e730aa9abbbe96a3c5281cb72b62a6d0eda47468efd1681132e263425b4f11')
  })
  it('sends the timestamp in Unix seconds of this try', () => {
    const headers = signedHeaders('formalie_hook_live_test', '{"id":"evt_1"}', 1767225600_999)
    expect(headers).toEqual({ 'Formalie-Timestamp': '1767225600', 'Formalie-Signature': webhookSignature('formalie_hook_live_test', 1767225600, '{"id":"evt_1"}') })
  })
  it('changes with the body, the time and the token', () => {
    const base = webhookSignature('t1', 1, 'a')
    expect(webhookSignature('t1', 1, 'b')).not.toBe(base)
    expect(webhookSignature('t1', 2, 'a')).not.toBe(base)
    expect(webhookSignature('t2', 1, 'a')).not.toBe(base)
  })
})

describe('the Node.js receiver sample, run as shown', () => {
  type Check = (headers: Record<string, string>, rawBody: Buffer, token: string) => boolean | string
  // The Node.js sample exactly as the webhook's Checking a delivery tab shows it (Verify.vue)
  const source = readFileSync(join(__dirname, '../../app/components/integrations/webhooks/Verify.vue'), 'utf8')
  const start = source.indexOf('javascript: [') + 'javascript: '.length
  const lines = source.slice(start, source.indexOf("].join('\\n'),", start) + 1)
  const sample = (new Function(`return ${lines}`)() as string[]).join('\n')
  // The sample's import becomes a parameter; everything else runs exactly as a customer would copy it
  const fromFormalie = new Function('crypto', `${sample.replace("import { createHmac, timingSafeEqual } from 'node:crypto'", 'const { createHmac, timingSafeEqual } = crypto')}\nreturn fromFormalie`)(crypto) as Check
  const token = 'formalie_hook_live_sample'
  const body = '{"id":"evt_1","type":"response.created"}'
  const delivery = (key: string, at = Date.now(), sentBody = body) => ({ ...signedHeaders(token, sentBody, at), 'Formalie-Key': key })
  const lower = (headers: Record<string, string>) => Object.fromEntries(Object.entries(headers).map(([name, value]) => [name.toLowerCase(), value]))

  it('accepts a delivery the mock signed, once', () => {
    const headers = lower(delivery('dlv_a'))
    expect(fromFormalie(headers, Buffer.from(body), token)).toBe(true)
    expect(fromFormalie(headers, Buffer.from(body), token)).toBe('already handled')
  })
  it('refuses a changed body, another token, or a missing signature', () => {
    expect(fromFormalie(lower(delivery('dlv_b')), Buffer.from(body.replace('created', 'deleted')), token)).toBe(false)
    expect(fromFormalie(lower(delivery('dlv_c')), Buffer.from(body), 'formalie_hook_live_other')).toBe(false)
    const { 'formalie-signature': _signature, ...unsigned } = lower(delivery('dlv_d'))
    expect(fromFormalie(unsigned, Buffer.from(body), token)).toBe(false)
  })
  it('refuses a delivery more than 5 minutes old', () => {
    expect(fromFormalie(lower(delivery('dlv_e', Date.now() - 6 * 60_000)), Buffer.from(body), token)).toBe(false)
    expect(fromFormalie(lower(delivery('dlv_f', Date.now() - 4 * 60_000)), Buffer.from(body), token)).toBe(true)
  })
})

describe('daily caps per address (security review L19)', () => {
  it('allows 5 copies of answers a day to one address, whatever its case', () => {
    const now = Date.UTC(2026, 9, 13)
    for (let i = 0; i < RECEIPTS_PER_ADDRESS_PER_DAY; i++) expect(underDailyCap('test-receipts', i % 2 ? 'Sam@Example.com' : 'sam@example.com', RECEIPTS_PER_ADDRESS_PER_DAY, now)).toBe(true)
    expect(underDailyCap('test-receipts', 'sam@example.com', RECEIPTS_PER_ADDRESS_PER_DAY, now)).toBe(false)
    expect(underDailyCap('test-receipts', 'other@example.com', RECEIPTS_PER_ADDRESS_PER_DAY, now)).toBe(true)
    // A day later it starts again
    expect(underDailyCap('test-receipts', 'sam@example.com', RECEIPTS_PER_ADDRESS_PER_DAY, now + 86_400_001)).toBe(true)
  })
  it('allows 10 verification codes a day to one address', () => {
    const now = Date.UTC(2026, 9, 13)
    for (let i = 0; i < CODES_PER_ADDRESS_PER_DAY; i++) expect(underDailyCap('test-codes', 'kim@example.com', CODES_PER_ADDRESS_PER_DAY, now + i)).toBe(true)
    expect(underDailyCap('test-codes', 'kim@example.com', CODES_PER_ADDRESS_PER_DAY, now + 20)).toBe(false)
  })
})

describe('unsubscribe links (security review L19, L22)', () => {
  const locales = join(__dirname, '../../i18n/locales')
  it('lets a respondent stop copies of their answers', () => {
    expect(UNSUBSCRIBE_KINDS).toContain('response_receipt')
  })
  it('names every kind on the unsubscribe page in all 20 languages', () => {
    const files = readdirSync(locales).filter(file => file.endsWith('.json'))
    expect(files).toHaveLength(20)
    for (const file of files) {
      const what = JSON.parse(readFileSync(join(locales, file), 'utf8')).emailPrefs.what
      // New responses and notifications have their own phrasings (responsesTo / notification)
      for (const kind of UNSUBSCRIBE_KINDS.filter(item => item !== 'response_notification' && item !== 'notification')) expect(what[kind], `${file} ${kind}`).toBeTruthy()
    }
  })
  it('treats the token as opaque, up to 800 characters', () => {
    expect(UNSUBSCRIBE_TOKEN_MAX).toBe(800)
    const page = readFileSync(join(__dirname, '../../app/pages/email/unsubscribe.vue'), 'utf8')
    // The page passes `t` on as it came: no splitting, decoding or length cut
    expect(page).not.toMatch(/token\.(split|slice|substring)|atob\(|JSON\.parse\(/)
  })
})

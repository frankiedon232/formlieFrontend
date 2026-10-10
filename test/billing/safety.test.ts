import { describe, expect, it } from 'vitest'
import { canMove, checkIdempotency, pruneIdempotency, renewalReference, requestHash, signWebhook, verifyWebhook, type IdempotencyRecord } from '../../server/mock/billing/safety'

describe('money safety', () => {
  it('answers a repeated request key with the first result and refuses it for another request', () => {
    const hash = requestHash('change', { plan: 'business', period: 'annually' })
    expect(requestHash('change', { period: 'annually', plan: 'business' })).toBe(hash)
    const records: IdempotencyRecord<string>[] = [{ key: 'k1', scope: 'change', hash, result: 'first', at: new Date().toISOString() }]
    expect(checkIdempotency(records, 'k1', 'change', hash)).toEqual({ kind: 'replay', result: 'first' })
    expect(checkIdempotency(records, 'k1', 'change', requestHash('change', { plan: 'professional', period: 'monthly' }))).toEqual({ kind: 'conflict' })
    expect(checkIdempotency(records, 'k2', 'change', hash)).toEqual({ kind: 'new' })
  })

  it('forgets request keys after 24 hours', () => {
    const old = new Date(Date.now() - 25 * 3_600_000).toISOString()
    const records: IdempotencyRecord[] = [{ key: 'k1', scope: 's', hash: 'h', result: 1, at: old }]
    expect(checkIdempotency(records, 'k1', 's', 'h')).toEqual({ kind: 'new' })
    expect(pruneIdempotency(records)).toHaveLength(0)
  })

  it('gives each renewal period one reference', () => {
    expect(renewalReference('ws1', '2026-11-30T10:00:00.000Z')).toBe('renew:ws1:2026-11-30')
    expect(renewalReference('ws1', '2026-11-30T23:59:00.000Z')).toBe(renewalReference('ws1', '2026-11-30T00:00:00.000Z'))
  })

  it('accepts only signed, fresh webhooks', () => {
    const body = JSON.stringify({ id: 'evt_1', type: 'payment.succeeded' })
    const now = Math.floor(Date.now() / 1000)
    const header = signWebhook('secret', body, now)
    expect(verifyWebhook('secret', body, header, now)).toBe('ok')
    expect(verifyWebhook('other', body, header, now)).toBe('bad_signature')
    expect(verifyWebhook('secret', body + ' ', header, now)).toBe('bad_signature')
    expect(verifyWebhook('secret', body, header, now + 301)).toBe('stale')
    expect(verifyWebhook('secret', body, null, now)).toBe('missing')
  })

  it('only moves payments forward', () => {
    expect(canMove('pending', 'paid')).toBe(true)
    expect(canMove('paid', 'pending')).toBe(false)
    expect(canMove('paid', 'failed')).toBe(false)
    expect(canMove('failed', 'paid')).toBe(true)
    expect(canMove('paid', 'refunded')).toBe(true)
    expect(canMove('paid', 'paid')).toBe(false)
  })
})

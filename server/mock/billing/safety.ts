/**
 * Money safety rules (F24, owner 2026-10-10; docs/SECURITY-PROTOCOL.md → Payments). Pure, so they are tested on
 * their own (test/billing/safety.test.ts) and the backend follows the same rules:
 *
 *   - Idempotency: every request that can move money carries a request key chosen by the app for one decision.
 *     The same key with the same request returns the first result (never a second charge); the same key with a
 *     different request is refused. Keys are remembered for 24 hours.
 *   - Payment references: every charge has one unique reference (a checkout, an upgrade, or `renew:{workspace}:{period end}`)
 *     sent to the processor, so a retried renewal or upgrade can't be charged twice on either side.
 *   - Webhooks: signed with the shared secret over `{timestamp}.{body}` (HMAC-SHA256), at most 5 minutes old, and
 *     each event handled once. The processor's real format replaces the placeholder when Payoneer's docs are in.
 */
import { createHash, createHmac, timingSafeEqual } from 'node:crypto'

export const IDEMPOTENCY_HOURS = 24
export const WEBHOOK_TOLERANCE_SECONDS = 300

export interface IdempotencyRecord<T = unknown> {
  key: string
  scope: string
  hash: string
  result: T
  at: string
}

/** A stable fingerprint of a request (key order doesn't matter). */
export function requestHash(scope: string, body: unknown): string {
  const canonical = (value: unknown): unknown =>
    Array.isArray(value) ? value.map(canonical) : value && typeof value === 'object' ? Object.fromEntries(Object.keys(value as object).sort().map(key => [key, canonical((value as Record<string, unknown>)[key])])) : value
  return createHash('sha256').update(`${scope}:${JSON.stringify(canonical(body))}`).digest('hex')
}

export type IdempotencyCheck<T> = { kind: 'new' } | { kind: 'replay'; result: T } | { kind: 'conflict' }

/** What to do with a request key: run it, answer with the first result, or refuse (same key, other request). */
export function checkIdempotency<T>(records: IdempotencyRecord<T>[], key: string, scope: string, hash: string, now = Date.now()): IdempotencyCheck<T> {
  const found = records.find(item => item.key === key && now - Date.parse(item.at) < IDEMPOTENCY_HOURS * 3_600_000)
  if (!found) return { kind: 'new' }
  return found.scope === scope && found.hash === hash ? { kind: 'replay', result: found.result } : { kind: 'conflict' }
}

/** Keeps the records of the last 24 hours (at most 200 per workspace). */
export const pruneIdempotency = <T>(records: IdempotencyRecord<T>[], now = Date.now()) => records.filter(item => now - Date.parse(item.at) < IDEMPOTENCY_HOURS * 3_600_000).slice(0, 200)

/** The one reference of a renewal charge: the same period can only ever be charged once. */
export const renewalReference = (workspaceId: string, periodEnd: string) => `renew:${workspaceId}:${periodEnd.slice(0, 10)}`

/** `t=…,v1=…` signature over `{t}.{body}`. */
export function signWebhook(secret: string, body: string, timestamp = Math.floor(Date.now() / 1000)) {
  return `t=${timestamp},v1=${createHmac('sha256', secret).update(`${timestamp}.${body}`).digest('hex')}`
}

export type WebhookCheck = 'ok' | 'missing' | 'stale' | 'bad_signature'

/** Checks a webhook's signature (constant time) and age. */
export function verifyWebhook(secret: string, body: string, header: string | null | undefined, now = Math.floor(Date.now() / 1000)): WebhookCheck {
  if (!header) return 'missing'
  const parts = Object.fromEntries(header.split(',').map(part => part.trim().split('=') as [string, string]))
  const timestamp = Number(parts.t)
  if (!parts.v1 || !Number.isFinite(timestamp)) return 'missing'
  if (Math.abs(now - timestamp) > WEBHOOK_TOLERANCE_SECONDS) return 'stale'
  const expected = Buffer.from(createHmac('sha256', secret).update(`${timestamp}.${body}`).digest('hex'))
  const given = Buffer.from(parts.v1)
  return expected.length === given.length && timingSafeEqual(expected, given) ? 'ok' : 'bad_signature'
}

export type PaymentStatus = 'pending' | 'paid' | 'failed' | 'refunded'
/** Payments only move forward: a late or repeated event never undoes a later state. */
const ORDER: Record<PaymentStatus, number> = { pending: 0, failed: 1, paid: 2, refunded: 3 }
export const canMove = (from: PaymentStatus, to: PaymentStatus) => from !== to && (ORDER[to] > ORDER[from] || (from === 'failed' && to === 'paid'))

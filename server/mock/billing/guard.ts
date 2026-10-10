/**
 * Guards around anything that moves money in the mock (F24; rules in ./safety.ts, docs/SECURITY-PROTOCOL.md → Payments):
 *
 *   - one billing change at a time per workspace (a second one at the same moment → 409 FRM-BILL-1004);
 *   - a request key per decision (`request_key` in the body): repeated → the first result, reused for another
 *     request → 409 FRM-BILL-1005, missing → FRM-GEN-1002;
 *   - every charge is written down as a payment (pending first, then paid / failed) under one unique reference,
 *     before the processor is asked, so a crash or retry never charges twice.
 */
import type { BillingPeriod, PlanId } from '#shared/types/billing'
import { MockError } from '../core/respond'
import { billingOf, saveBilling } from '../data/billingStore'
import type { MockTenant } from '../data/tenants'
import { checkIdempotency, pruneIdempotency, requestHash, type PaymentStatus } from './safety'

export interface StoredPayment {
  id: string
  /** The one reference sent to the processor (checkout id, `upgrade:{key}`, `renew:{workspace}:{period end}`). */
  reference: string
  kind: 'subscribe' | 'upgrade' | 'renewal' | 'card'
  plan: PlanId
  period: BillingPeriod
  amount: number
  currency: string
  status: PaymentStatus
  invoice_id: string | null
  created_at: string
  settled_at: string | null
}

const busy = new Set<string>()

/** Runs a billing change with the workspace's lock held. */
export async function withBillingLock<T>(tenant: MockTenant, work: () => T | Promise<T>): Promise<T> {
  if (busy.has(tenant.id)) throw new MockError('FRM-BILL-1004')
  busy.add(tenant.id)
  try {
    return await work()
  } finally {
    busy.delete(tenant.id)
  }
}

/** Runs `work` once per request key; a repeat answers with what the first one returned. */
export async function once<T>(tenant: MockTenant, scope: string, key: unknown, request: unknown, work: () => T | Promise<T>): Promise<T> {
  if (typeof key !== 'string' || !/^[A-Za-z0-9_-]{16,80}$/.test(key)) throw new MockError('FRM-GEN-1002', [{ field: 'request_key', message: 'required' }])
  const billing = billingOf(tenant)
  billing.requests = pruneIdempotency(billing.requests ?? [])
  const hash = requestHash(scope, request)
  const check = checkIdempotency(billing.requests, key, scope, hash)
  if (check.kind === 'replay') return check.result as T
  if (check.kind === 'conflict') throw new MockError('FRM-BILL-1005')
  const result = await work()
  billing.requests = [{ key, scope, hash, result, at: new Date().toISOString() }, ...billingOf(tenant).requests!]
  saveBilling()
  return result
}

/** Writes a charge down as pending under its reference (an existing one with that reference is returned instead). */
export function recordPayment(tenant: MockTenant, input: Omit<StoredPayment, 'id' | 'status' | 'invoice_id' | 'created_at' | 'settled_at'>): { payment: StoredPayment; existing: boolean } {
  const billing = billingOf(tenant)
  billing.payments ??= []
  const existing = billing.payments.find(item => item.reference === input.reference)
  if (existing) return { payment: existing, existing: true }
  const payment: StoredPayment = { ...input, id: crypto.randomUUID(), status: 'pending', invoice_id: null, created_at: new Date().toISOString(), settled_at: null }
  billing.payments.unshift(payment)
  billing.payments = billing.payments.slice(0, 500)
  saveBilling()
  return { payment, existing: false }
}

export function settlePayment(payment: StoredPayment, status: Exclude<PaymentStatus, 'pending'>, invoiceId: string | null = payment.invoice_id) {
  payment.status = status
  payment.invoice_id = invoiceId
  payment.settled_at = new Date().toISOString()
  saveBilling()
}

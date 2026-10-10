/**
 * POST /billing/webhooks/payoneer (F24): the payment processor's notifications, the only thing that confirms a
 * payment in the backend (never the browser coming back from the checkout). Plain request, no session.
 *
 *   1. Signature: `Payoneer-Signature: t={unix seconds},v1={HMAC-SHA256 of "{t}.{raw body}"}` with the shared
 *      secret (runtime config `payoneerWebhookSecret`), checked in constant time, at most 5 minutes old.
 *   2. Each event is handled once (its id is remembered); a repeat answers 200 without doing anything.
 *   3. The payment is found by its one reference; the amount and currency must match what was written down.
 *   4. Payments only move forward (pending → paid / failed → paid → refunded); a late or repeated event never
 *      undoes a later state. The backend also asks the processor for the payment's status before acting.
 *
 * PLACEHOLDER FORMAT until Payoneer's documentation is in (owner is opening the account):
 *   { id, type: payment.succeeded | payment.failed | payment.refunded, data: { reference, amount, currency } }
 * Anything that fails a check → 400 FRM-BILL-1006 (audited as a warning), nothing changes.
 */
import { z } from 'zod'
import { recordAudit } from '../core/audit'
import { loadPersisted, savePersisted } from '../core/persist'
import { billingOf, saveBilling } from '../data/billingStore'
import { MOCK_TENANTS } from '../data/tenants'
import { canMove, verifyWebhook, type PaymentStatus } from './safety'

const DEV_SECRET = 'formalie-dev-webhook-secret'
const handled: string[] = loadPersisted<string[]>('billing-events', [])
const remember = (id: string) => {
  handled.unshift(id)
  handled.length = Math.min(handled.length, 5000)
  savePersisted('billing-events', () => handled)
}

const eventSchema = z.object({
  id: z.string().min(1).max(100),
  type: z.enum(['payment.succeeded', 'payment.failed', 'payment.refunded']),
  data: z.object({ reference: z.string().min(1).max(200), amount: z.number().finite(), currency: z.string().length(3) }),
})
const STATUS: Record<z.infer<typeof eventSchema>['type'], PaymentStatus> = { 'payment.succeeded': 'paid', 'payment.failed': 'failed', 'payment.refunded': 'refunded' }

const refuse = (reason: string) => {
  console.warn(`[mock-billing] webhook refused: ${reason}`)
  return { status: 400, body: { error: { code: 'FRM-BILL-1006', reason } } }
}

export function receivePayoneerEvent(secretFromConfig: string, raw: string, signature: string | null | undefined, now = Math.floor(Date.now() / 1000)) {
  const secret = secretFromConfig || (import.meta.dev ? DEV_SECRET : '')
  if (!secret) return refuse('no_secret')
  const check = verifyWebhook(secret, raw, signature, now)
  if (check !== 'ok') return refuse(check)
  let event: z.infer<typeof eventSchema>
  try {
    event = eventSchema.parse(JSON.parse(raw))
  } catch {
    return refuse('format')
  }
  if (handled.includes(event.id)) return { status: 200, body: { ok: true, duplicate: true } }
  for (const tenant of MOCK_TENANTS) {
    const billing = billingOf(tenant)
    const payment = billing.payments?.find(item => item.reference === event.data.reference)
    if (!payment) continue
    if (Math.abs(payment.amount - event.data.amount) > 0.005 || payment.currency !== event.data.currency.toUpperCase()) return refuse('amount_mismatch')
    const next = STATUS[event.type]
    remember(event.id)
    if (!canMove(payment.status, next)) return { status: 200, body: { ok: true, ignored: payment.status } }
    payment.status = next
    payment.settled_at = new Date().toISOString()
    const invoice = billing.invoices.find(item => item.id === payment.invoice_id)
    if (invoice) invoice.status = next === 'paid' ? 'paid' : next === 'refunded' ? 'refunded' : 'failed'
    saveBilling()
    return { status: 200, body: { ok: true }, applied: { tenant, reference: payment.reference, id: payment.id, status: next } }
  }
  return refuse('unknown_reference')
}

/** The route: reads the raw body (the signature is over the exact bytes). */
export const payoneerWebhook = defineEventHandler(async event => {
  const raw = (await readRawBody(event, 'utf8')) ?? ''
  const result = receivePayoneerEvent(useRuntimeConfig(event).payoneerWebhookSecret as string, raw, getHeader(event, 'payoneer-signature'))
  if ('applied' in result && result.applied) {
    const { tenant, reference, id, status } = result.applied
    recordAudit(event, tenant, { action: 'settings.updated', actor: { type: 'system', id: null, name: 'Payoneer', email: null }, resource: { type: 'setting', id, name: 'Payment' }, changes: [{ field: 'payment_status', before: null, after: `${reference}: ${status}` }] })
  }
  setResponseStatus(event, result.status)
  return result.body
})

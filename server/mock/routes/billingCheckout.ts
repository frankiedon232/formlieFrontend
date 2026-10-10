/**
 * Paying and saving a card (F24). Card details never reach Formalie: the processor (Payoneer) takes them on
 * its hosted checkout and tells the backend the result (webhook). The mock has no processor yet, so the app
 * shows a test step and the mock "completes" the checkout with a test card (brand and last four only).
 *
 *   POST /billing/checkout                 { plan, period, request_key } (subscribe) or { purpose: 'add_card', request_key } → CheckoutSession
 *                                          (one open checkout per workspace: a new one cancels the one before)
 *   POST /billing/checkout/:id/complete    mock only: { outcome: paid | declined, brand } (the processor's webhook, simulated)
 *   GET  /billing/checkout/:id             the session (status after returning from the processor)
 */
import { z } from 'zod'
import { BILLING_PERIODS, PLAN_IDS, type CheckoutSession, type PaymentMethod } from '#shared/types/billing'
import { actorOf, recordAudit } from '../core/audit'
import { requireAuth } from '../core/auth'
import { MockError, ok } from '../core/respond'
import { defineMockRoute } from '../core/route'
import { parseBody } from '../core/validate'
import { billingOf, saveBilling } from '../data/billingStore'
import { cardLabel, refreshNextCharge, retryOverdue } from '../data/billingLifecycle'
import { planChange, startPlan } from './billing'
import { once, recordPayment, settlePayment, withBillingLock } from '../billing/guard'

const startSchema = z.union([
  z.object({ purpose: z.literal('add_card'), request_key: z.string() }),
  z.object({ purpose: z.literal('subscribe').optional(), plan: z.enum(PLAN_IDS), period: z.enum(BILLING_PERIODS), request_key: z.string() }),
])

/** One open checkout per workspace: starting one cancels the one before (two can never both be paid). */
export const startCheckout = defineMockRoute(({ event, body }) => {
  const { tenant } = requireAuth(event)
  const { request_key: key, ...input } = parseBody(startSchema, body)
  return withBillingLock(tenant, () =>
    once(tenant, 'checkout', key, input, () => {
      const billing = billingOf(tenant)
      const sub = billing.subscription
      let session: CheckoutSession
      const base = { id: crypto.randomUUID(), url: null, expires_at: new Date(Date.now() + 30 * 60_000).toISOString() }
      if (input.purpose === 'add_card') session = { ...base, plan: sub.plan, period: sub.period, amount: 0, currency: 'USD', purpose: 'add_card' }
      else {
        const change = planChange(tenant, input.plan, input.period)
        if (change.when !== 'now') throw new MockError('FRM-GEN-1002', [{ field: 'plan', message: 'period_end' }])
        session = { ...base, plan: input.plan, period: input.period, amount: change.due, currency: change.target.currency, purpose: 'subscribe' }
        // Written down before the processor sees it: the checkout's id is the payment's one reference
        recordPayment(tenant, { reference: `checkout:${session.id}`, kind: 'subscribe', plan: session.plan, period: session.period, amount: session.amount, currency: session.currency })
      }
      // Earlier open checkouts are cancelled (their pending payments fail)
      for (const old of billing.checkouts) {
        const payment = billing.payments?.find(item => item.reference === `checkout:${old.id}` && item.status === 'pending')
        if (payment) settlePayment(payment, 'failed')
      }
      billing.checkouts = [session]
      saveBilling()
      return session
    }),
  ).then(session => ok(session))
})

const completeSchema = z.object({ outcome: z.enum(['paid', 'declined']), brand: z.enum(['visa', 'mastercard', 'amex', 'discover']).default('visa') })
const TEST_LAST4: Record<string, string> = { visa: '4242', mastercard: '4444', amex: '8431', discover: '1117' }

/**
 * The processor's answer for a checkout (mock only; the backend learns it from the signed webhook). The checkout's
 * id is the request key: answering twice returns the first result, never a second plan start or charge.
 */
export const completeCheckout = defineMockRoute(({ event, body }) => {
  const { tenant, user } = requireAuth(event)
  const input = parseBody(completeSchema, body)
  const id = getRouterParam(event, 'id') ?? ''
  return withBillingLock(tenant, () =>
    once(tenant, 'complete', id, input, () => {
      const billing = billingOf(tenant)
      const session = billing.checkouts.find(item => item.id === id)
      if (!session) throw new MockError('FRM-GEN-1004')
      if (Date.parse(session.expires_at) < Date.now()) throw new MockError('FRM-BILL-1002')
      billing.checkouts = billing.checkouts.filter(item => item.id !== id)
      const payment = billing.payments?.find(item => item.reference === `checkout:${session.id}`)
      if (input.outcome === 'declined') {
        if (payment) settlePayment(payment, 'failed')
        saveBilling()
        recordAudit(event, tenant, { action: 'settings.updated', actor: actorOf(user), outcome: 'failure', reason: 'FRM-BILL-1001', resource: { type: 'setting', id: null, name: 'Subscription' } })
        throw new MockError('FRM-BILL-1001')
      }
      const sub = billing.subscription
      const before = cardLabel(sub)
      const now = new Date()
      const card: PaymentMethod = { brand: input.brand, last4: TEST_LAST4[input.brand]!, exp_month: 12, exp_year: now.getUTCFullYear() + 3, reference: `pm_test_${crypto.randomUUID().slice(0, 12)}`, added_at: now.toISOString() }
      sub.payment_method = card
      if (session.purpose === 'subscribe') {
        sub.auto_renew = true
        const invoice = startPlan(tenant, session.plan, session.period, session.amount, now)
        if (payment) settlePayment(payment, 'paid', invoice.id)
        recordAudit(event, tenant, { action: 'settings.updated', actor: actorOf(user), resource: { type: 'setting', id: null, name: 'Subscription' }, changes: [{ field: 'plan', before: null, after: `${session.plan} (${session.period})` }, { field: 'payment_method', before, after: cardLabel(sub) }] })
      } else {
        // A card added while past due pays the period that failed (same reference, never a second charge)
        retryOverdue(tenant)
        refreshNextCharge(sub)
        saveBilling()
        recordAudit(event, tenant, { action: 'settings.updated', actor: actorOf(user), resource: { type: 'setting', id: null, name: 'Subscription' }, changes: [{ field: 'payment_method', before, after: cardLabel(sub) }] })
      }
      return { done: true }
    }),
  ).then(result => ok(result))
})

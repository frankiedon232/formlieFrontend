/**
 * What happens to a subscription as time passes (the backend runs this on a schedule; the mock runs it
 * whenever billing is read): at the end of a period a cancelled plan becomes Starter, a scheduled change
 * starts, an automatic renewal charges the card (a new invoice), and without a card the subscription is
 * past due with a grace period; after the grace period it expires to Starter. Each period's renewal is one
 * payment under `renew:{workspace}:{period end}`, so running this twice never charges twice.
 */
import type { MockTenant } from './tenants'
import { GRACE_DAYS, billingOf, makeInvoice, saveBilling } from './billingStore'
import { periodEnd, planOf } from '#shared/utils/billing/plans'
import type { Subscription } from '#shared/types/billing'
import { recordPayment, settlePayment } from '../billing/guard'
import { renewalReference } from '../billing/safety'

export const cardLabel = (sub: Subscription) => (sub.payment_method ? `${sub.payment_method.brand === 'other' ? 'Card' : sub.payment_method.brand[0]!.toUpperCase() + sub.payment_method.brand.slice(1)} •••• ${sub.payment_method.last4}` : null)

function toStarter(sub: Subscription, now: Date) {
  Object.assign(sub, { plan: 'starter', period: 'monthly', status: 'active', current_period_start: null, current_period_end: null, auto_renew: false, cancel_at_period_end: false, scheduled: null, grace_until: null, next_charge: null, started_at: now.toISOString() })
}

/** The next charge, from the plan, period and renewal choice. */
export function refreshNextCharge(sub: Subscription) {
  const plan = planOf(sub.scheduled?.plan ?? sub.plan)
  const period = sub.scheduled?.period ?? sub.period
  const price = plan.prices?.[period] ?? 0
  sub.next_charge = sub.current_period_end && sub.auto_renew && !sub.cancel_at_period_end && price > 0 ? { amount: price, currency: plan.currency, at: sub.current_period_end } : null
}

export function advance(tenant: MockTenant, now = new Date()) {
  const billing = billingOf(tenant)
  const sub = billing.subscription
  let changed = false
  // Grace over: back to Starter
  if (sub.status === 'past_due' && sub.grace_until && Date.parse(sub.grace_until) <= now.getTime()) {
    toStarter(sub, now)
    sub.status = 'expired'
    changed = true
  }
  while (sub.current_period_end && Date.parse(sub.current_period_end) <= now.getTime() && sub.status !== 'past_due') {
    const end = new Date(sub.current_period_end)
    if (sub.cancel_at_period_end) {
      toStarter(sub, now)
      changed = true
      break
    }
    if (sub.scheduled) {
      sub.plan = sub.scheduled.plan
      sub.period = sub.scheduled.period
      sub.scheduled = null
      if (sub.plan === 'starter') {
        toStarter(sub, now)
        changed = true
        break
      }
    }
    const price = planOf(sub.plan).prices?.[sub.period] ?? 0
    if (!sub.auto_renew) {
      toStarter(sub, now)
      sub.status = 'expired'
      changed = true
      break
    }
    if (!sub.payment_method) {
      // Renewal couldn't be charged: everything keeps working through the grace period
      sub.status = 'past_due'
      sub.grace_until = new Date(end.getTime() + GRACE_DAYS * 86_400_000).toISOString()
      const { payment, existing } = recordPayment(tenant, { reference: renewalReference(tenant.id, end.toISOString()), kind: 'renewal', plan: sub.plan, period: sub.period, amount: price, currency: planOf(sub.plan).currency })
      if (!existing) {
        const invoice = makeInvoice(sub.plan, sub.period, end, periodEnd(end, sub.period), price, null, 'failed')
        billing.invoices.unshift(invoice)
        settlePayment(payment, 'failed', invoice.id)
      }
      changed = true
      break
    }
    const next = periodEnd(end, sub.period)
    // One reference per period, written down before the card is charged: a renewal run twice never charges twice
    const { payment, existing } = recordPayment(tenant, { reference: renewalReference(tenant.id, end.toISOString()), kind: 'renewal', plan: sub.plan, period: sub.period, amount: price, currency: planOf(sub.plan).currency })
    if (!existing || payment.status === 'pending') {
      const invoice = makeInvoice(sub.plan, sub.period, end, next, price, cardLabel(sub))
      billing.invoices.unshift(invoice)
      settlePayment(payment, 'paid', invoice.id)
    }
    sub.current_period_start = end.toISOString()
    sub.current_period_end = next.toISOString()
    changed = true
  }
  refreshNextCharge(sub)
  if (changed) saveBilling()
  return billing
}

/**
 * A card added while past due pays the period that failed, under the same reference (failed → paid), then the
 * subscription is active again. Returns whether it was charged.
 */
export function retryOverdue(tenant: MockTenant): boolean {
  const billing = billingOf(tenant)
  const sub = billing.subscription
  if (sub.status !== 'past_due' || !sub.payment_method || !sub.current_period_end) return false
  const end = new Date(sub.current_period_end)
  const payment = billing.payments?.find(item => item.reference === renewalReference(tenant.id, end.toISOString()))
  if (!payment || payment.status === 'paid') return false
  const next = periodEnd(end, sub.period)
  const invoice = billing.invoices.find(item => item.id === payment.invoice_id)
  if (invoice) Object.assign(invoice, { status: 'paid', card: cardLabel(sub) })
  settlePayment(payment, 'paid', invoice?.id ?? null)
  Object.assign(sub, { status: 'active', grace_until: null, current_period_start: end.toISOString(), current_period_end: next.toISOString() })
  refreshNextCharge(sub)
  saveBilling()
  return true
}

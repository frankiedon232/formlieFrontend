/**
 * What happens to a subscription as time passes (the backend runs this on a schedule; the mock runs it
 * whenever billing is read): at the end of a period a cancelled plan becomes Starter, a scheduled change
 * starts, an automatic renewal charges the card (a new invoice), and without a card the subscription is
 * past due with a grace period; after the grace period it expires to Starter.
 */
import type { MockTenant } from './tenants'
import { GRACE_DAYS, billingOf, makeInvoice, saveBilling } from './billingStore'
import { periodEnd, planOf } from '#shared/utils/billing/plans'
import type { Subscription } from '#shared/types/billing'

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
      billing.invoices.unshift(makeInvoice(sub.plan, sub.period, end, periodEnd(end, sub.period), price, null, 'failed'))
      changed = true
      break
    }
    const next = periodEnd(end, sub.period)
    billing.invoices.unshift(makeInvoice(sub.plan, sub.period, end, next, price, cardLabel(sub)))
    sub.current_period_start = end.toISOString()
    sub.current_period_end = next.toISOString()
    changed = true
  }
  refreshNextCharge(sub)
  if (changed) saveBilling()
  return billing
}

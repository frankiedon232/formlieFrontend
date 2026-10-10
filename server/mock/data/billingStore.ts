/**
 * Subscriptions in the mock (F24), kept in `.data/mock/billing.json`: each workspace's plan, period, card
 * (brand, last four, expiry and the processor's reference only), renewal and reminders, invoices and open
 * checkouts. Every workspace holds a plan and it is active at once: new ones start on Starter; the sample
 * workspaces start on Business (Remedy Legal) and Starter (the others), so every limit can be tried.
 */
import type { BillingPeriod, CheckoutSession, Invoice, PlanId, Subscription } from '#shared/types/billing'
import { periodEnd, planOf } from '#shared/utils/billing/plans'
import { loadPersisted, savePersisted } from '../core/persist'
import type { MockTenant } from './tenants'
import type { IdempotencyRecord } from '../billing/safety'
import type { StoredPayment } from '../billing/guard'

export interface StoredBilling {
  subscription: Subscription
  invoices: Invoice[]
  checkouts: CheckoutSession[]
  /** Reminders already announced (key: kind + period end), so each goes out once. */
  reminded: string[]
  /** Request keys of the last 24 hours (idempotency, billing/safety.ts). */
  requests?: IdempotencyRecord[]
  /** Every charge, written down before the processor is asked (billing/guard.ts). */
  payments?: StoredPayment[]
}

const stores = new Map<string, StoredBilling>(Object.entries(loadPersisted<Record<string, StoredBilling>>('billing', {})))
export const saveBilling = () => savePersisted('billing', () => Object.fromEntries(stores))

export const DEFAULT_REMINDERS = { before_renewal: [7, 1], payment_failed: true, card_expiring: true, extra_emails: [] as string[] }
/** Days of grace after a failed renewal before the workspace turns read-only. */
export const GRACE_DAYS = 7

let invoiceSeq = 1000
const nextNumber = () => `FRM-${new Date().getUTCFullYear()}-${String(++invoiceSeq).padStart(5, '0')}`

export function makeInvoice(plan: PlanId, period: BillingPeriod, start: Date, end: Date, amount: number, card: string | null, status: Invoice['status'] = 'paid'): Invoice {
  return { id: crypto.randomUUID(), number: nextNumber(), issued_at: start.toISOString(), plan, period, period_start: start.toISOString(), period_end: end.toISOString(), amount, currency: planOf(plan).currency, status, card }
}

function seed(tenant: MockTenant): StoredBilling {
  const now = new Date()
  const free = (): Subscription => ({ plan: 'starter', period: 'monthly', status: 'active', started_at: now.toISOString(), current_period_start: null, current_period_end: null, auto_renew: false, cancel_at_period_end: false, scheduled: null, grace_until: null, payment_method: null, reminders: { ...DEFAULT_REMINDERS }, next_charge: null })
  if (tenant.subdomain !== 'remedylegal') return { subscription: free(), invoices: [], checkouts: [], reminded: [] }
  // The sample workspace: Business, paid yearly, renews in about seven weeks
  const start = new Date(now.getTime() - 314 * 86_400_000)
  const end = periodEnd(start, 'annually')
  const plan = planOf('business')
  const amount = plan.prices!.annually
  const card = { brand: 'visa' as const, last4: '4242', exp_month: 8, exp_year: now.getUTCFullYear() + 2, reference: 'pm_test_sample', added_at: start.toISOString() }
  const earlier = periodEnd(new Date(start.getTime() - 366 * 86_400_000), 'annually')
  return {
    subscription: { plan: 'business', period: 'annually', status: 'active', started_at: new Date(start.getTime() - 366 * 86_400_000).toISOString(), current_period_start: start.toISOString(), current_period_end: end.toISOString(), auto_renew: true, cancel_at_period_end: false, scheduled: null, grace_until: null, payment_method: card, reminders: { ...DEFAULT_REMINDERS }, next_charge: { amount, currency: plan.currency, at: end.toISOString() } },
    invoices: [makeInvoice('business', 'annually', start, end, amount, 'Visa •••• 4242'), makeInvoice('professional', 'annually', new Date(start.getTime() - 366 * 86_400_000), earlier, planOf('professional').prices!.annually, 'Visa •••• 4242')],
    checkouts: [],
    reminded: [],
  }
}

/** The workspace's billing record; created (and active) the first time it is needed. */
export function billingOf(tenant: MockTenant): StoredBilling {
  let billing = stores.get(tenant.id)
  if (!billing) {
    billing = seed(tenant)
    stores.set(tenant.id, billing)
    saveBilling()
  }
  return billing
}

/** The plan the workspace holds right now (an expired paid plan counts as Starter). */
export function currentPlan(tenant: MockTenant) {
  const { subscription } = billingOf(tenant)
  return planOf(subscription.status === 'expired' || subscription.status === 'cancelled' ? 'starter' : subscription.plan)
}

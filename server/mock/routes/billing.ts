/**
 * Subscription (F24, docs/API-CONTRACT.md → Billing). Reading: settings.view; changing: settings.manage;
 * the plans are open to every member (upgrade prompts).
 *
 *   GET    /billing                         subscription, its plan, usage
 *   GET    /billing/plans                   the plans and prices
 *   GET    /billing/invoices                newest first
 *   POST   /billing/preview                 { plan, period } → when it starts, what is due now, what goes over
 *   POST   /billing/change                  { plan, period } → changed now (upgrade with a card), scheduled
 *                                           (downgrade / shorter period at the end), or a checkout to pay first
 *   POST   /billing/cancel · /billing/resume · DELETE /billing/scheduled
 *   PATCH  /billing/settings                { auto_renew?, reminders? }
 *   DELETE /billing/payment-method          removes the card (renewal then needs a new one)
 *
 * Checkouts and the card (processor) live in billingCheckout.ts. Everything is audited.
 */
import type { H3Event } from 'h3'
import { z } from 'zod'
import { BILLING_PERIODS, PLAN_IDS, type BillingOverview, type BillingPeriod, type DowngradeImpact, type Plan, type PlanId, type PlanUsage } from '#shared/types/billing'
import { PLANS, periodEnd, planOf, planRank, prorationCredit } from '#shared/utils/billing/plans'
import { actorOf, recordAudit } from '../core/audit'
import { requireAuth } from '../core/auth'
import { MockError, ok } from '../core/respond'
import { defineMockRoute } from '../core/route'
import { parseBody } from '../core/validate'
import { addressOf } from '../data/addressStore'
import { creditsUsed } from '../data/aiStore'
import { billingOf, makeInvoice, saveBilling } from '../data/billingStore'
import { advance, cardLabel, refreshNextCharge } from '../data/billingLifecycle'
import { dataSourcesOf } from '../data/dataSourceStore'
import { formsOf } from '../data/formStore'
import { sendingOf } from '../data/sendingStore'
import { settingsOf } from '../data/settingsStore'
import { ssoOf } from '../data/ssoStore'
import type { MockTenant, MockUser } from '../data/tenants'

export function usageOf(tenant: MockTenant): PlanUsage {
  const forms = formsOf(tenant).forms.filter(form => !form.deleted_at)
  const top = [...forms].sort((a, b) => b.responses_count - a.responses_count)[0]
  return {
    forms: forms.length,
    top_form: top ? { id: top.id, name: top.name, responses: top.responses_count } : null,
    databases: [...new Set(dataSourcesOf(tenant).map(source => source.engine))],
    ai_credits_used: creditsUsed(tenant),
    custom_domain: !!addressOf(tenant).domain,
    custom_email: sendingOf(tenant).mode !== 'formalie',
    sso: !!ssoOf(tenant),
    social_signin: settingsOf(tenant).signin.methods.some(method => method !== 'password'),
  }
}

/** What would go over a plan's limits with today's use. */
export function impactOf(tenant: MockTenant, plan: Plan): DowngradeImpact {
  const usage = usageOf(tenant)
  const limits = plan.limits
  const over: DowngradeImpact['over'] = []
  if (limits.forms !== null && usage.forms > limits.forms) over.push({ key: 'forms', current: usage.forms, allowed: limits.forms })
  if (limits.responses_per_form !== null && usage.top_form && usage.top_form.responses > limits.responses_per_form) over.push({ key: 'responses', current: usage.top_form.responses, allowed: limits.responses_per_form })
  const extra = usage.databases.filter(engine => !limits.databases.includes(engine))
  if (extra.length) over.push({ key: 'databases', current: extra.join(', '), allowed: limits.databases.join(', ') })
  if (usage.custom_domain && limits.custom_domains === 0) over.push({ key: 'customDomain', current: 1, allowed: 0 })
  if (usage.custom_email && !limits.custom_email) over.push({ key: 'customEmail', current: 1, allowed: 0 })
  if (usage.sso && !limits.sso) over.push({ key: 'sso', current: 1, allowed: 0 })
  if (usage.social_signin && !limits.social_signin) over.push({ key: 'socialSignin', current: 1, allowed: 0 })
  return { plan: plan.id, over }
}

const overview = (tenant: MockTenant): BillingOverview => {
  const { subscription } = advance(tenant)
  return { subscription, plan: planOf(subscription.plan), usage: usageOf(tenant) }
}
const audit = (event: H3Event, tenant: MockTenant, user: MockUser, field: string, before: string | null, after: string | null) =>
  recordAudit(event, tenant, { action: 'settings.updated', actor: actorOf(user), resource: { type: 'setting', id: null, name: 'Subscription' }, changes: [{ field, before, after }] })
const label = (plan: PlanId, period: BillingPeriod) => `${plan} (${period})`

export const getBilling = defineMockRoute(({ event }) => ok(overview(requireAuth(event).tenant)))
export const getPlans = defineMockRoute(({ event }) => (requireAuth(event), ok(PLANS)))
export const getInvoices = defineMockRoute(({ event }) => {
  const { tenant } = requireAuth(event)
  return ok(advance(tenant).invoices)
})

const changeSchema = z.object({ plan: z.enum(PLAN_IDS), period: z.enum(BILLING_PERIODS) })

/** When a change starts and what it costs now: upgrades start now (less the unused part), the rest at the period's end. */
export function planChange(tenant: MockTenant, plan: PlanId, period: BillingPeriod, now = new Date()) {
  const sub = advance(tenant, now).subscription
  const target = planOf(plan)
  if (!target.prices) throw new MockError('FRM-GEN-1002', [{ field: 'plan', message: 'contact' }])
  const current = planOf(sub.plan)
  const price = target.prices[period]
  const paidNow = sub.current_period_start && sub.current_period_end && current.prices ? current.prices[sub.period] : 0
  const upgrade = planRank(plan) > planRank(sub.plan) || (plan === sub.plan && period !== sub.period && price > (current.prices?.[sub.period] ?? 0))
  const fromFree = sub.plan === 'starter' || !sub.current_period_end
  const when: 'now' | 'period_end' = fromFree || upgrade ? 'now' : 'period_end'
  const credit = when === 'now' && !fromFree ? prorationCredit(paidNow, new Date(sub.current_period_start!), new Date(sub.current_period_end!), now) : 0
  return { target, price, when, credit, due: when === 'now' ? Math.max(0, Math.round((price - credit) * 100) / 100) : 0, starts_at: when === 'now' ? now.toISOString() : sub.current_period_end! }
}

export const previewChange = defineMockRoute(({ event, body }) => {
  const { tenant } = requireAuth(event)
  const input = parseBody(changeSchema, body)
  const change = planChange(tenant, input.plan, input.period)
  return ok({ plan: input.plan, period: input.period, price: change.price, currency: change.target.currency, when: change.when, starts_at: change.starts_at, credit: change.credit, due_now: change.due, impact: impactOf(tenant, change.target) })
})

/** Starts a paid plan now, charged to the card on file (the processor confirms in the backend). */
export function startPlan(tenant: MockTenant, plan: PlanId, period: BillingPeriod, amount: number, now = new Date()) {
  const billing = billingOf(tenant)
  const sub = billing.subscription
  const end = periodEnd(now, period)
  Object.assign(sub, { plan, period, status: 'active', current_period_start: now.toISOString(), current_period_end: end.toISOString(), cancel_at_period_end: false, scheduled: null, grace_until: null })
  if (!sub.auto_renew && sub.payment_method) sub.auto_renew = true
  billing.invoices.unshift(makeInvoice(plan, period, now, end, amount, cardLabel(sub)))
  refreshNextCharge(sub)
  saveBilling()
}

export const changePlan = defineMockRoute(({ event, body }) => {
  const { tenant, user } = requireAuth(event)
  const input = parseBody(changeSchema, body)
  const billing = billingOf(tenant)
  const sub = billing.subscription
  const before = label(sub.plan, sub.period)
  // Moving down to Starter is cancelling at the end of the period
  if (input.plan === 'starter') {
    if (sub.plan === 'starter') return ok({ overview: overview(tenant), checkout: null })
    sub.cancel_at_period_end = true
    sub.scheduled = null
    refreshNextCharge(sub)
    saveBilling()
    audit(event, tenant, user, 'plan', before, 'starter (at period end)')
    return ok({ overview: overview(tenant), checkout: null })
  }
  const change = planChange(tenant, input.plan, input.period)
  if (change.when === 'period_end') {
    sub.scheduled = { plan: input.plan, period: input.period, at: change.starts_at }
    sub.cancel_at_period_end = false
    refreshNextCharge(sub)
    saveBilling()
    audit(event, tenant, user, 'plan', before, `${label(input.plan, input.period)} (at period end)`)
    return ok({ overview: overview(tenant), checkout: null })
  }
  // Paying now needs a card: without one, the processor's checkout takes the payment and saves the card
  if (!sub.payment_method) return ok({ overview: overview(tenant), checkout: { plan: input.plan, period: input.period, amount: change.due } })
  startPlan(tenant, input.plan, input.period, change.due)
  audit(event, tenant, user, 'plan', before, label(input.plan, input.period))
  return ok({ overview: overview(tenant), checkout: null })
})

export const cancelPlan = defineMockRoute(({ event }) => {
  const { tenant, user } = requireAuth(event)
  const sub = billingOf(tenant).subscription
  if (sub.plan === 'starter') throw new MockError('FRM-GEN-1002', [{ field: 'plan', message: 'free' }])
  sub.cancel_at_period_end = true
  sub.scheduled = null
  refreshNextCharge(sub)
  saveBilling()
  audit(event, tenant, user, 'cancel_at_period_end', 'false', 'true')
  return ok(overview(tenant))
})

export const resumePlan = defineMockRoute(({ event }) => {
  const { tenant, user } = requireAuth(event)
  const sub = billingOf(tenant).subscription
  sub.cancel_at_period_end = false
  refreshNextCharge(sub)
  saveBilling()
  audit(event, tenant, user, 'cancel_at_period_end', 'true', 'false')
  return ok(overview(tenant))
})

export const dropScheduled = defineMockRoute(({ event }) => {
  const { tenant, user } = requireAuth(event)
  const sub = billingOf(tenant).subscription
  const before = sub.scheduled ? label(sub.scheduled.plan, sub.scheduled.period) : null
  sub.scheduled = null
  refreshNextCharge(sub)
  saveBilling()
  audit(event, tenant, user, 'scheduled_change', before, null)
  return ok(overview(tenant))
})

const settingsSchema = z.object({
  auto_renew: z.boolean().optional(),
  reminders: z
    .object({
      before_renewal: z.array(z.union([z.literal(30), z.literal(14), z.literal(7), z.literal(3), z.literal(1)])).max(5),
      payment_failed: z.boolean(),
      card_expiring: z.boolean(),
      extra_emails: z.array(z.string().trim().toLowerCase().pipe(z.email())).max(5),
    })
    .optional(),
})

export const patchBillingSettings = defineMockRoute(({ event, body }) => {
  const { tenant, user } = requireAuth(event)
  const input = parseBody(settingsSchema, body)
  const sub = billingOf(tenant).subscription
  if (input.auto_renew !== undefined && input.auto_renew !== sub.auto_renew) {
    audit(event, tenant, user, 'auto_renew', String(sub.auto_renew), String(input.auto_renew))
    sub.auto_renew = input.auto_renew
  }
  if (input.reminders) {
    audit(event, tenant, user, 'reminders', JSON.stringify(sub.reminders.before_renewal), JSON.stringify(input.reminders.before_renewal))
    sub.reminders = { ...input.reminders, before_renewal: [...new Set(input.reminders.before_renewal)].sort((a, b) => b - a) }
  }
  refreshNextCharge(sub)
  saveBilling()
  return ok(overview(tenant))
})

export const removePaymentMethod = defineMockRoute(({ event }) => {
  const { tenant, user } = requireAuth(event)
  const sub = billingOf(tenant).subscription
  const before = cardLabel(sub)
  if (before) {
    sub.payment_method = null
    saveBilling()
    audit(event, tenant, user, 'payment_method', before, null)
  }
  return ok(overview(tenant))
})

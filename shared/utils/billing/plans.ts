/**
 * The plans (owner 2026-10-10) and the billing maths, shared by the app and the mock. Prices are provisional
 * until the owner sets them; the API (platform admin) serves the real ones in the same shape.
 * Quarterly is 10% off and annually 20% off the monthly price; amounts are rounded to whole cents.
 */
import type { BillingPeriod, Plan, PlanFeature, PlanId, PlanLimits } from '#shared/types/billing'

const EVERYONE: PlanFeature[] = ['analytics', 'templates', 'lists', 'themes', 'explorer', 'query', 'destinations', 'api', 'webhooks', 'apiDocs', 'ai', 'branding', 'subdomain', 'languages', 'visits', 'versions', 'folders', 'fillLater']
const PAID: PlanFeature[] = [...EVERYONE, 'socialSignin', 'sso', 'customDomain', 'customEmail']

export const PERIOD_MONTHS: Record<BillingPeriod, number> = { monthly: 1, quarterly: 3, annually: 12 }
export const PERIOD_DISCOUNT: Record<BillingPeriod, number> = { monthly: 0, quarterly: 0.1, annually: 0.2 }

const cents = (value: number) => Math.round(value * 100) / 100
/** The whole period's price from a monthly price. */
export const periodPrice = (monthly: number, period: BillingPeriod) => cents(monthly * PERIOD_MONTHS[period] * (1 - PERIOD_DISCOUNT[period]))
const pricesFrom = (monthly: number) => ({ monthly: periodPrice(monthly, 'monthly'), quarterly: periodPrice(monthly, 'quarterly'), annually: periodPrice(monthly, 'annually') })

const ALL_DATABASES: PlanLimits['databases'] = ['mysql', 'postgresql', 'sqlserver', 'oracle', 'mariadb']

export const PLANS: Plan[] = [
  {
    id: 'starter',
    prices: { monthly: 0, quarterly: 0, annually: 0 },
    currency: 'USD',
    limits: { forms: 5, responses_per_form: 10_000, databases: ['mysql'], social_signin: false, sso: false, custom_domains: 0, custom_email: false, data_residency: false, ai_credits: 100, languages: 20 },
    features: EVERYONE,
  },
  {
    id: 'professional',
    prices: pricesFrom(19),
    currency: 'USD',
    limits: { forms: 20, responses_per_form: 200_000, databases: ['mysql', 'postgresql', 'mariadb'], social_signin: true, sso: true, custom_domains: 1, custom_email: true, data_residency: false, ai_credits: 500, languages: 20 },
    features: [...PAID, 'prioritySupport'],
    recommended: true,
  },
  {
    id: 'business',
    prices: pricesFrom(49),
    currency: 'USD',
    limits: { forms: null, responses_per_form: null, databases: ALL_DATABASES, social_signin: true, sso: true, custom_domains: null, custom_email: true, data_residency: false, ai_credits: 2000, languages: 20 },
    features: [...PAID, 'prioritySupport'],
  },
  {
    id: 'enterprise',
    prices: null,
    currency: 'USD',
    limits: { forms: null, responses_per_form: null, databases: ALL_DATABASES, social_signin: true, sso: true, custom_domains: null, custom_email: true, data_residency: true, ai_credits: null, languages: 20 },
    features: [...PAID, 'prioritySupport', 'dedicatedSupport', 'securityReview', 'dataResidency'],
  },
]

export const planOf = (id: PlanId, plans: Plan[] = PLANS) => plans.find(plan => plan.id === id) ?? plans[0]!
/** Order for "upgrade" / "downgrade". */
export const planRank = (id: PlanId) => ['starter', 'professional', 'business', 'enterprise'].indexOf(id)
/** The price per month for a period (what the toggle shows big). */
export const monthlyEquivalent = (plan: Plan, period: BillingPeriod) => (plan.prices ? cents(plan.prices[period] / PERIOD_MONTHS[period]) : null)
/** What a period saves against paying monthly for the same months. */
export const periodSaving = (plan: Plan, period: BillingPeriod) => (plan.prices ? cents(plan.prices.monthly * PERIOD_MONTHS[period] - plan.prices[period]) : 0)

/** The end of a period that starts at `from`. */
export function periodEnd(from: Date, period: BillingPeriod): Date {
  const end = new Date(from)
  end.setUTCMonth(end.getUTCMonth() + PERIOD_MONTHS[period])
  return end
}

/** The unused part of the current period as a credit when upgrading now (whole cents). */
export function prorationCredit(paid: number, start: Date, end: Date, now: Date) {
  const total = end.getTime() - start.getTime()
  if (total <= 0 || now >= end) return 0
  return cents(paid * Math.max(0, end.getTime() - now.getTime()) / total)
}

/** Does a plan allow a value? (null limit = no limit) */
export const withinLimit = (limit: number | null, value: number) => limit === null || value <= limit

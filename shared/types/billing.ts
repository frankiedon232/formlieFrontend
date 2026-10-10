/**
 * Plans and subscriptions (F24, owner 2026-10-10; docs/API-CONTRACT.md → Billing). Prices and limits come
 * from Formalie's API (set in the platform admin); the catalogue in shared/utils/billing/plans.ts is the
 * starting set. Card details never reach Formalie: the processor (Payoneer) keeps them, Formalie keeps the
 * brand, the last four digits, the expiry and the processor's reference.
 */
import type { DbEngine } from '#shared/utils/integrations/databases'

export const PLAN_IDS = ['starter', 'professional', 'business', 'enterprise'] as const
export type PlanId = (typeof PLAN_IDS)[number]
export const BILLING_PERIODS = ['monthly', 'quarterly', 'annually'] as const
export type BillingPeriod = (typeof BILLING_PERIODS)[number]

/** What a plan allows; null = no limit. */
export interface PlanLimits {
  forms: number | null
  responses_per_form: number | null
  /** The databases a workspace may connect (Bring your database). */
  databases: DbEngine[]
  /** Google, Apple, Microsoft, Facebook and single sign-on; off = email and password only. */
  social_signin: boolean
  sso: boolean
  /** 0 = none. */
  custom_domains: number | null
  custom_email: boolean
  /** Data kept in a region the workspace chooses (leftovers L7). */
  data_residency: boolean
  ai_credits: number | null
  languages: number
}

/** Rows of the comparison, in order; each plan lists the ones it includes. */
export const PLAN_FEATURES = [
  'analytics',
  'templates',
  'lists',
  'themes',
  'explorer',
  'query',
  'destinations',
  'api',
  'webhooks',
  'apiDocs',
  'ai',
  'branding',
  'subdomain',
  'languages',
  'visits',
  'versions',
  'folders',
  'fillLater',
  'socialSignin',
  'sso',
  'customDomain',
  'customEmail',
  'dataResidency',
  'prioritySupport',
  'dedicatedSupport',
  'securityReview',
] as const
export type PlanFeature = (typeof PLAN_FEATURES)[number]

export interface Plan {
  id: PlanId
  /** The price for each billing period (the whole period), in the plan's currency; null = contact us. */
  prices: Record<BillingPeriod, number> | null
  currency: string
  limits: PlanLimits
  features: PlanFeature[]
  /** Shown as "Most popular". */
  recommended?: boolean
}

export type SubscriptionStatus = 'active' | 'past_due' | 'grace' | 'cancelled' | 'expired'

export interface PaymentMethod {
  brand: 'visa' | 'mastercard' | 'amex' | 'discover' | 'other'
  last4: string
  exp_month: number
  exp_year: number
  /** The processor's reference (never the card number). */
  reference: string
  added_at: string
}

/** Reminders the workspace gets (on by default). */
export interface BillingReminders {
  /** Days before renewal: any of 30, 14, 7, 3, 1. */
  before_renewal: number[]
  payment_failed: boolean
  card_expiring: boolean
  /** Who gets them besides the owner. */
  extra_emails: string[]
}

export interface Subscription {
  plan: PlanId
  period: BillingPeriod
  status: SubscriptionStatus
  started_at: string
  /** The current period; null on the free plan. */
  current_period_start: string | null
  current_period_end: string | null
  auto_renew: boolean
  /** Cancelled: stays on the plan until the period ends, then Starter. */
  cancel_at_period_end: boolean
  /** A downgrade or period change waiting for the end of the period. */
  scheduled: { plan: PlanId; period: BillingPeriod; at: string } | null
  /** Grace after a failed payment: everything works until then, then read-only. */
  grace_until: string | null
  payment_method: PaymentMethod | null
  reminders: BillingReminders
  /** The next charge (null on the free plan or when it won't renew). */
  next_charge: { amount: number; currency: string; at: string } | null
}

export interface PlanUsage {
  forms: number
  /** The form closest to its response limit. */
  top_form: { id: string; name: string; responses: number } | null
  databases: DbEngine[]
  ai_credits_used: number
  custom_domain: boolean
  custom_email: boolean
  sso: boolean
  social_signin: boolean
}

/** GET /billing */
export interface BillingOverview {
  subscription: Subscription
  plan: Plan
  usage: PlanUsage
}

export interface Invoice {
  id: string
  number: string
  issued_at: string
  plan: PlanId
  period: BillingPeriod
  period_start: string
  period_end: string
  amount: number
  currency: string
  status: 'paid' | 'open' | 'failed' | 'refunded'
  card: string | null
}

/** What would stop working after moving to a smaller plan. */
export interface DowngradeImpact {
  plan: PlanId
  over: { key: 'forms' | 'responses' | 'databases' | 'customDomain' | 'customEmail' | 'sso' | 'socialSignin'; current: number | string; allowed: number | string }[]
}

/** POST /billing/checkout → the processor's hosted checkout (the mock simulates it). */
export interface CheckoutSession {
  id: string
  /** Payoneer's hosted page; the mock leaves it null and the app shows its test step. */
  url: string | null
  plan: PlanId
  period: BillingPeriod
  amount: number
  currency: string
  /** add_card = only save a card for renewals. */
  purpose: 'subscribe' | 'add_card'
  expires_at: string
}


/**
 * The plan someone picked on the website (formalieSite docs/SIGNUP-FLOW.md, 2026-10-13): its "Start free" and plan
 * buttons open the portal's sign-up with `?plan=starter|professional|business&period=monthly|quarterly|annually`.
 * Starter when the plan is missing or unknown, Monthly when the period is (the website's pricing page opens on
 * Monthly too); Enterprise is not signed up for here, the website's enquiry takes it. A paid plan opens its checkout
 * once the workspace exists; closing it leaves the workspace on Starter with a way to finish later.
 */
import { BILLING_PERIODS, PLAN_IDS, type BillingPeriod, type PlanId } from '#shared/types/billing'

export const DEFAULT_SIGNUP_PERIOD: BillingPeriod = 'monthly'

export interface SignupPlan {
  plan: PlanId
  period: BillingPeriod
}

const one = (value: unknown) => (Array.isArray(value) ? value[0] : value)

/** The plan and period from the sign-up address. */
export function signupPlanFrom(query: Record<string, unknown>): SignupPlan {
  const plan = String(one(query.plan) ?? '').toLowerCase()
  const period = String(one(query.period) ?? '').toLowerCase()
  return {
    plan: (PLAN_IDS as readonly string[]).includes(plan) ? (plan as PlanId) : 'starter',
    period: (BILLING_PERIODS as readonly string[]).includes(period) ? (period as BillingPeriod) : DEFAULT_SIGNUP_PERIOD,
  }
}

/** Professional or Business: paid in the portal's checkout after the workspace is created. */
export const isPaidSignup = (choice: SignupPlan | null | undefined): choice is SignupPlan =>
  !!choice && choice.plan !== 'starter' && choice.plan !== 'enterprise'

/** The hand-off to the new workspace carries a paid choice along (`…/auth/welcome?ticket=…&plan=…&period=…`). */
export function withSignupPlan(url: string, choice: SignupPlan | null | undefined): string {
  if (!isPaidSignup(choice)) return url
  const next = new URL(url)
  next.searchParams.set('plan', choice.plan)
  next.searchParams.set('period', choice.period)
  return next.toString()
}

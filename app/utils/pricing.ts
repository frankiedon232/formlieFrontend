/**
 * Pricing maths and the comparison table (docs/PRICING.md), from the plans of GET /public/plans. Pure, so it is
 * unit-tested; the pricing page only adds the words.
 */
import type { DatabaseEngine, Plan } from './plans'

export type Period = 'monthly' | 'quarterly' | 'annually'
export const PERIODS: Period[] = ['monthly', 'quarterly', 'annually']
export const PERIOD_MONTHS: Record<Period, number> = { monthly: 1, quarterly: 3, annually: 12 }

const cents = (amount: number) => Math.round(amount * 100) / 100

/** The price per month when paying for the chosen period (the big number on a plan card). */
export function pricePerMonth(plan: Plan, period: Period): number | null {
  if (!plan.prices) return null
  return cents(plan.prices[period] / PERIOD_MONTHS[period])
}

/** The saving against paying monthly, in whole percent (10 for quarterly, 20 for annually with the samples). */
export function savingPercent(plan: Plan, period: Period): number {
  if (!plan.prices || !plan.prices.monthly) return 0
  const full = plan.prices.monthly * PERIOD_MONTHS[period]
  return Math.max(0, Math.round((1 - plan.prices[period] / full) * 100))
}

/** The largest saving any plan offers for a period (shown on the period toggle). */
export function bestSaving(plans: Plan[], period: Period): number {
  return Math.max(0, ...plans.map(plan => savingPercent(plan, period)))
}

/** A cell of the comparison table: included or not, a number, unlimited or custom. */
export type Cell = boolean | number | 'unlimited' | 'custom'

export interface ComparisonRow {
  /** i18n key under pricingPage.rows. */
  key: string
  /** For the database rows, the engine (its name is shown as it is). */
  engine?: DatabaseEngine
  cells: Partial<Record<Plan['id'], Cell>>
}

export interface ComparisonGroup {
  key: string
  rows: ComparisonRow[]
}

const ENGINE_ORDER: DatabaseEngine[] = ['mysql', 'postgresql', 'mariadb', 'sqlserver', 'oracle']

/**
 * The full comparison, grouped like the app's Settings → Plans, built from what each plan says it includes
 * (`features`, `limits`), so the table follows the platform admin.
 */
export function comparison(plans: Plan[]): ComparisonGroup[] {
  const row = (key: string, cell: (plan: Plan) => Cell, engine?: DatabaseEngine): ComparisonRow => ({
    key,
    engine,
    cells: Object.fromEntries(plans.map(plan => [plan.id, cell(plan)])),
  })
  const has = (feature: string) => (plan: Plan) => plan.features.includes(feature)
  /** null means no limit; `zeroIsNone` turns 0 into "not included". */
  const limit =
    (pick: (plan: Plan) => number | null, zeroIsNone = false, nullIs: 'unlimited' | 'custom' = 'unlimited') =>
    (plan: Plan): Cell => {
      const value = pick(plan)
      if (value === null) return nullIs
      if (zeroIsNone && value === 0) return false
      return value
    }

  return [
    {
      key: 'forms',
      rows: [
        row(
          'forms',
          limit(plan => plan.limits.forms),
        ),
        row(
          'responses',
          limit(plan => plan.limits.responses_per_form),
        ),
        row('languages', plan => plan.limits.languages),
        row('templates', has('templates')),
        row('lists', has('lists')),
        row('themes', has('themes')),
        row('versions', has('versions')),
        row('folders', has('folders')),
        row('fillLater', has('fillLater')),
      ],
    },
    {
      key: 'insight',
      rows: [
        row('analytics', has('analytics')),
        row('visits', has('visits')),
        row('ai', has('ai')),
        row(
          'aiCredits',
          limit(plan => plan.limits.ai_credits, false, 'custom'),
        ),
      ],
    },
    {
      key: 'data',
      rows: [
        ...ENGINE_ORDER.map(engine =>
          row('database', plan => plan.limits.databases.includes(engine), engine),
        ),
        row('explorer', has('explorer')),
        row('query', has('query')),
        row('destinations', has('destinations')),
      ],
    },
    {
      key: 'api',
      rows: [row('api', has('api')), row('webhooks', has('webhooks')), row('apiDocs', has('apiDocs'))],
    },
    {
      key: 'brand',
      rows: [
        row('branding', has('branding')),
        row('subdomain', has('subdomain')),
        row(
          'customDomain',
          limit(plan => plan.limits.custom_domains, true),
        ),
        row('customEmail', plan => plan.limits.custom_email),
        row('residency', plan => plan.limits.data_residency),
      ],
    },
    {
      key: 'signin',
      rows: [
        row('password', () => true),
        row('social', plan => plan.limits.social_signin),
        row('sso', plan => plan.limits.sso),
      ],
    },
    {
      key: 'support',
      rows: [
        row('help', () => true),
        row('priority', has('prioritySupport')),
        row('dedicated', has('dedicatedSupport')),
        row('review', has('securityReview')),
      ],
    },
  ]
}

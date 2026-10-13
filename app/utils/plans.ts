/**
 * Plans and prices (docs/API-HOOKS.md, docs/PRICING.md): the shape of GET {API}/public/plans, checked before use,
 * and the sample copy used when the API doesn't answer. Pure, so it is unit-tested.
 */
import { z } from 'zod'
import fallback from '~/data/plans.json'

const ENGINES = ['mysql', 'postgresql', 'sqlserver', 'oracle', 'mariadb'] as const
export type DatabaseEngine = (typeof ENGINES)[number]

/** Database names as their makers write them. */
export const ENGINE_NAMES: Record<DatabaseEngine, string> = {
  mysql: 'MySQL',
  postgresql: 'PostgreSQL',
  mariadb: 'MariaDB',
  sqlserver: 'SQL Server',
  oracle: 'Oracle',
}

const planSchema = z.object({
  id: z.enum(['starter', 'professional', 'business', 'enterprise']),
  prices: z.object({ monthly: z.number(), quarterly: z.number(), annually: z.number() }).nullable(),
  currency: z.string().default('USD'),
  limits: z.object({
    forms: z.number().nullable(),
    responses_per_form: z.number().nullable(),
    // Unknown engines from a newer backend are dropped rather than failing the whole list.
    databases: z
      .array(z.string())
      .transform(list => list.filter((e): e is DatabaseEngine => (ENGINES as readonly string[]).includes(e))),
    social_signin: z.boolean().default(true),
    sso: z.boolean(),
    custom_domains: z.number().nullable(),
    custom_email: z.boolean(),
    data_residency: z.boolean(),
    ai_credits: z.number().nullable(),
    languages: z.number(),
  }),
  features: z.array(z.string()),
  recommended: z.boolean().optional(),
})

export type Plan = z.infer<typeof planSchema>
export type PlansSource = 'api' | 'fallback'

const ORDER: Plan['id'][] = ['starter', 'professional', 'business', 'enterprise']

/** Checks an API answer (`{ success, data }`); null when it isn't a usable list of plans. */
export function parsePlans(answer: unknown): Plan[] | null {
  const envelope = z.object({ success: z.literal(true), data: z.array(z.unknown()) }).safeParse(answer)
  if (!envelope.success) return null
  const plans = envelope.data.data.flatMap(item => {
    const plan = planSchema.safeParse(item)
    return plan.success ? [plan.data] : []
  })
  if (!plans.length) return null
  return plans.sort((a, b) => ORDER.indexOf(a.id) - ORDER.indexOf(b.id))
}

/** The sample plans from docs/PRICING.md. */
export function fallbackPlans(): Plan[] {
  return parsePlans({ success: true, data: fallback.plans }) ?? []
}

/** A price in the visitor's language, without cents when it is a whole amount. */
export function formatPrice(amount: number, currency: string, locale: string): string {
  const whole = Number.isInteger(amount)
  return new Intl.NumberFormat(locale, {
    style: 'currency',
    currency,
    minimumFractionDigits: whole ? 0 : 2,
    maximumFractionDigits: whole ? 0 : 2,
  }).format(amount)
}

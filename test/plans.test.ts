import { describe, expect, it } from 'vitest'
import { fallbackPlans, formatPrice, parsePlans } from '../app/utils/plans'

const live = {
  success: true,
  data: [
    {
      id: 'business',
      prices: { monthly: 49, quarterly: 132.3, annually: 470.4 },
      currency: 'USD',
      limits: {
        forms: null,
        responses_per_form: null,
        databases: ['mysql', 'postgresql', 'sqlserver', 'oracle', 'mariadb', 'cockroach'],
        sso: true,
        custom_domains: null,
        custom_email: true,
        data_residency: false,
        ai_credits: 2000,
        languages: 20,
      },
      features: ['analytics'],
    },
    {
      id: 'starter',
      prices: { monthly: 0, quarterly: 0, annually: 0 },
      currency: 'USD',
      limits: {
        forms: 5,
        responses_per_form: 10000,
        databases: ['mysql'],
        sso: false,
        custom_domains: 0,
        custom_email: false,
        data_residency: false,
        ai_credits: 100,
        languages: 20,
      },
      features: [],
    },
    { id: 'unknown-plan' },
  ],
  meta: {},
}

describe('plans from GET /public/plans (docs/API-HOOKS.md)', () => {
  it('keeps valid plans in order, drops broken ones and unknown engines', () => {
    const plans = parsePlans(live)!
    expect(plans.map(plan => plan.id)).toEqual(['starter', 'business'])
    expect(plans[1]!.limits.databases).toEqual(['mysql', 'postgresql', 'sqlserver', 'oracle', 'mariadb'])
    // social_signin is missing from the live answer: it is on every plan.
    expect(plans[0]!.limits.social_signin).toBe(true)
  })

  it('refuses answers that are not a successful list', () => {
    expect(parsePlans({ success: false, data: [] })).toBeNull()
    expect(parsePlans({ success: true, data: [] })).toBeNull()
    expect(parsePlans('<html>')).toBeNull()
  })

  it('has the four sample plans as a fallback, Professional recommended', () => {
    const plans = fallbackPlans()
    expect(plans.map(plan => plan.id)).toEqual(['starter', 'professional', 'business', 'enterprise'])
    expect(plans.find(plan => plan.recommended)?.id).toBe('professional')
    expect(plans.find(plan => plan.id === 'enterprise')?.prices).toBeNull()
  })

  it('formats prices without cents for whole amounts', () => {
    expect(formatPrice(19, 'USD', 'en')).toBe('$19')
    expect(formatPrice(15.2, 'USD', 'en')).toBe('$15.20')
  })
})

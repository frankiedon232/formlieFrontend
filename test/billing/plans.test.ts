import { describe, expect, it } from 'vitest'
import { PLANS, monthlyEquivalent, periodEnd, periodPrice, periodSaving, planOf, planRank, prorationCredit, withinLimit } from '../../shared/utils/billing/plans'

describe('billing plans', () => {
  it('has the four plans in order, Starter free and Enterprise priced on request', () => {
    expect(PLANS.map(plan => plan.id)).toEqual(['starter', 'professional', 'business', 'enterprise'])
    expect(planOf('starter').prices).toEqual({ monthly: 0, quarterly: 0, annually: 0 })
    expect(planOf('enterprise').prices).toBeNull()
    expect(planRank('business')).toBeGreaterThan(planRank('professional'))
  })

  it('follows the owner\'s limits', () => {
    expect(planOf('starter').limits).toMatchObject({ forms: 5, responses_per_form: 10_000, databases: ['mysql'], sso: false, custom_domains: 0, custom_email: false })
    expect(planOf('professional').limits).toMatchObject({ forms: 20, responses_per_form: 200_000, databases: ['mysql', 'postgresql', 'mariadb'], sso: true, social_signin: true, custom_domains: 1, custom_email: true })
    expect(planOf('business').limits).toMatchObject({ forms: null, responses_per_form: null, sso: true })
    expect(planOf('business').limits.databases).toHaveLength(5)
  })

  it('discounts quarterly by 10% and annually by 20%', () => {
    expect(periodPrice(19, 'monthly')).toBe(19)
    expect(periodPrice(19, 'quarterly')).toBe(51.3)
    expect(periodPrice(19, 'annually')).toBe(182.4)
    const pro = planOf('professional')
    expect(monthlyEquivalent(pro, 'annually')).toBe(15.2)
    expect(periodSaving(pro, 'annually')).toBe(45.6)
    expect(periodSaving(pro, 'monthly')).toBe(0)
  })

  it('works out period ends and the credit for unused time', () => {
    const start = new Date('2026-01-31T00:00:00Z')
    expect(periodEnd(new Date('2026-01-15T00:00:00Z'), 'quarterly').toISOString()).toBe('2026-04-15T00:00:00.000Z')
    expect(periodEnd(start, 'annually').toISOString()).toBe('2027-01-31T00:00:00.000Z')
    const from = new Date('2026-01-01T00:00:00Z')
    const to = new Date('2026-01-31T00:00:00Z')
    expect(prorationCredit(30, from, to, new Date('2026-01-16T00:00:00Z'))).toBe(15)
    expect(prorationCredit(30, from, to, new Date('2026-02-02T00:00:00Z'))).toBe(0)
  })

  it('treats null as no limit', () => {
    expect(withinLimit(null, 1_000_000)).toBe(true)
    expect(withinLimit(5, 5)).toBe(true)
    expect(withinLimit(5, 6)).toBe(false)
  })
})

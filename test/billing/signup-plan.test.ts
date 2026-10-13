import { describe, expect, it } from 'vitest'
import { DEFAULT_SIGNUP_PERIOD, isPaidSignup, signupPlanFrom, withSignupPlan } from '../../shared/utils/billing/signupPlan'
import { enterpriseUrl, LEGAL_SLUGS, legalUrl } from '../../shared/utils/urls/public'

describe('the plan picked on the website (formalieSite SIGNUP-FLOW)', () => {
  it('reads plan and period from the sign-up address', () => {
    expect(signupPlanFrom({ plan: 'professional', period: 'annually' })).toEqual({ plan: 'professional', period: 'annually' })
    expect(signupPlanFrom({ plan: 'Business', period: 'QUARTERLY' })).toEqual({ plan: 'business', period: 'quarterly' })
    expect(signupPlanFrom({ plan: ['business', 'starter'], period: ['monthly'] })).toEqual({ plan: 'business', period: 'monthly' })
  })
  it('starts on Starter and Monthly when they are missing or unknown', () => {
    expect(DEFAULT_SIGNUP_PERIOD).toBe('monthly')
    expect(signupPlanFrom({})).toEqual({ plan: 'starter', period: 'monthly' })
    expect(signupPlanFrom({ plan: 'platinum', period: 'weekly' })).toEqual({ plan: 'starter', period: 'monthly' })
    expect(signupPlanFrom({ plan: 'professional' })).toEqual({ plan: 'professional', period: 'monthly' })
  })
  it('pays only for Professional and Business here (Enterprise goes to the website)', () => {
    expect(isPaidSignup({ plan: 'professional', period: 'monthly' })).toBe(true)
    expect(isPaidSignup({ plan: 'business', period: 'annually' })).toBe(true)
    expect(isPaidSignup({ plan: 'starter', period: 'monthly' })).toBe(false)
    expect(isPaidSignup({ plan: 'enterprise', period: 'monthly' })).toBe(false)
    expect(isPaidSignup(null)).toBe(false)
  })
  it('carries a paid choice along on the hand-off to the new workspace', () => {
    const handOff = 'https://acme.formalie.dev:2202/auth/welcome?ticket=abc%2Bdef'
    expect(withSignupPlan(handOff, { plan: 'business', period: 'annually' })).toBe('https://acme.formalie.dev:2202/auth/welcome?ticket=abc%2Bdef&plan=business&period=annually')
    expect(withSignupPlan(handOff, { plan: 'starter', period: 'monthly' })).toBe(handOff)
    expect(withSignupPlan(handOff, null)).toBe(handOff)
  })
})

describe('links to the website', () => {
  it('builds the legal pages at /legal/{slug}', () => {
    expect(LEGAL_SLUGS).toEqual(['terms', 'privacy', 'data-protection', 'cookies', 'acceptable-use', 'subprocessors', 'refunds'])
    expect(legalUrl('https://formalie.dev:3033', 'privacy')).toBe('https://formalie.dev:3033/legal/privacy')
    expect(legalUrl('https://formalie.com/', 'terms')).toBe('https://formalie.com/legal/terms')
  })
  it('sends Enterprise to the website\'s enquiry', () => {
    expect(enterpriseUrl('https://formalie.com')).toBe('https://formalie.com/enterprise#enquiry')
  })
})

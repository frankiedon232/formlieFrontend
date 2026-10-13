import { describe, expect, it } from 'vitest'
import { apiUrl, findWorkspaceUrl, formEmbedUrl, FORM_KEYS, signupUrl } from '../app/utils/links'

const portal = 'https://manage.formalie.dev:2202/'

describe('portal links (docs/SIGNUP-FLOW.md)', () => {
  it('opens the sign-up on Starter without a period', () => {
    expect(signupUrl(portal, 'starter', 'annually')).toBe(
      'https://manage.formalie.dev:2202/auth/signup?plan=starter',
    )
    expect(signupUrl(portal)).toBe('https://manage.formalie.dev:2202/auth/signup')
  })

  it('passes the plan and period for paid plans', () => {
    expect(signupUrl(portal, 'professional', 'quarterly')).toBe(
      'https://manage.formalie.dev:2202/auth/signup?plan=professional&period=quarterly',
    )
  })

  it('signs in through find-workspace', () => {
    expect(findWorkspaceUrl(portal)).toBe('https://manage.formalie.dev:2202/auth/find-workspace')
  })
})

describe("Formalie's own forms", () => {
  it('builds the embed address with prefill, skipping empty values', () => {
    expect(
      formEmbedUrl('https://forms.formalie.dev:2202', FORM_KEYS.enterprise, {
        plan: 'business',
        email: undefined,
      }),
    ).toBe('https://forms.formalie.dev:2202/FormalieEn/embed?plan=business')
  })
})

describe('backend API', () => {
  it('joins the base and path with one slash', () => {
    expect(apiUrl('https://formalie.dev:5004/api/v1/', '/public/plans')).toBe(
      'https://formalie.dev:5004/api/v1/public/plans',
    )
  })
})

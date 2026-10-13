import { describe, expect, it } from 'vitest'
import { contentSecurityPolicy, headersFile, redirectsFile, securityHeaders } from '../deploy/headers'

const production = { api: 'https://services.formalie.com/api/v1', forms: 'https://forms.formalie.com' }

describe('security headers (docs/SECURITY.md)', () => {
  it('allows only this site, the backend API and Formalie form frames', () => {
    const csp = contentSecurityPolicy(production)
    expect(csp).toContain("connect-src 'self' https://services.formalie.com;")
    expect(csp).toContain('frame-src https://forms.formalie.com;')
    expect(csp).toContain("frame-ancestors 'none'")
    expect(csp).toContain("object-src 'none'")
    expect(csp).not.toContain('api.formalie.com')
  })

  it('adds the CSP only in production', () => {
    expect(securityHeaders(production, false)['Content-Security-Policy']).toBeUndefined()
    expect(securityHeaders(production, true)['X-Frame-Options']).toBe('DENY')
  })

  it('writes Cloudflare _headers and _redirects', () => {
    expect(headersFile(production)).toMatch(/^\/\*\n {2}Strict-Transport-Security/)
    expect(redirectsFile()).toContain('/terms /legal/terms 301')
    expect(redirectsFile()).toContain('/refunds /legal/refunds 301')
  })
})

import { readdirSync, readFileSync } from 'node:fs'
import { join } from 'node:path'
import { describe, expect, it } from 'vitest'
import { SAML_PROVIDERS_EXAMPLES, SSO_ICONS, SSO_NAMES, SSO_PROTOCOL, SSO_PROVIDERS } from '../../shared/types/sso'
import { ssoSaveSchema } from '../../server/mock/core/ssoSchema'
import { parseBody } from '../../server/mock/core/validate'
import { MockError } from '../../server/mock/core/respond'
import { ERROR_CODES } from '../../shared/utils/errors/codes'

describe('single sign-on choices (owner 2026-10-15)', () => {
  it('are Microsoft Entra ID, Google Workspace and SAML 2.0, in that order', () => {
    expect([...SSO_PROVIDERS]).toEqual(['entra', 'google_workspace', 'saml'])
  })
  it('keep Entra on OpenID Connect and the other two on SAML 2.0', () => {
    expect(SSO_PROTOCOL).toEqual({ entra: 'oidc', google_workspace: 'saml', saml: 'saml' })
  })
  it('have full names (Google Workspace is not the personal Google button) and an icon each', () => {
    expect(SSO_NAMES).toEqual({ entra: 'Microsoft Entra ID', google_workspace: 'Google Workspace', saml: 'SAML 2.0' })
    for (const provider of SSO_PROVIDERS) expect(SSO_ICONS[provider], provider).toMatch(/^i-(simple-icons|lucide)-/)
    expect(Object.keys(SSO_ICONS).sort()).toEqual([...SSO_PROVIDERS].sort())
  })
  it('name the common SAML 2.0 providers, so an Okta customer knows to pick it', () => {
    expect([...SAML_PROVIDERS_EXAMPLES]).toEqual(['Okta', 'OneLogin', 'JumpCloud', 'ADFS', 'Ping', 'Auth0', 'Keycloak'])
  })
})

describe('the Single sign-on form texts, in all 20 languages', () => {
  const dir = join(__dirname, '../../i18n/locales')
  const files = readdirSync(dir).filter(file => file.endsWith('.json'))
  it('have set-up steps for exactly the three choices', () => {
    expect(files).toHaveLength(20)
    for (const file of files) {
      const sso = JSON.parse(readFileSync(join(dir, file), 'utf8')).settings.sso
      expect(Object.keys(sso.how).sort(), file).toEqual([...SSO_PROVIDERS].sort())
      // The SAML 2.0 steps and the line under the choices list the common providers
      expect(sso.how.saml, file).toContain('{providers}')
      expect(sso.samlAny, file).toContain('{providers}')
    }
  })
  it('no longer offer Okta, OneLogin or OpenID Connect as choices of their own', () => {
    for (const file of files) {
      const sso = JSON.parse(readFileSync(join(dir, file), 'utf8')).settings.sso
      expect(JSON.stringify(sso), file).not.toMatch(/okta|onelogin/i)
    }
  })
})

describe('the mock accepts only the three choices', () => {
  const valid = { provider: 'saml', label: 'Acme', saml: { metadata_url: 'https://idp.example.com/metadata' }, domains: ['example.com'], enforce: false, auto_create: true, default_role: 'member' }
  it('saves Entra ID, Google Workspace and SAML 2.0', () => {
    for (const provider of SSO_PROVIDERS) expect(ssoSaveSchema.safeParse({ ...valid, provider }).success, provider).toBe(true)
  })
  it('refuses Okta, OneLogin and OpenID Connect with 422 FRM-GEN-1002, like any invalid value', () => {
    expect(ERROR_CODES['FRM-GEN-1002'].status).toBe(422)
    for (const provider of ['okta', 'onelogin', 'oidc', 'auth0']) {
      try {
        parseBody(ssoSaveSchema, { ...valid, provider })
        expect.unreachable(provider)
      } catch (error) {
        expect(error, provider).toBeInstanceOf(MockError)
        expect((error as MockError).code).toBe('FRM-GEN-1002')
        expect((error as MockError).details.map(detail => detail.field)).toContain('provider')
      }
    }
  })
})

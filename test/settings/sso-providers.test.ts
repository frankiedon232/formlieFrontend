import { readdirSync, readFileSync } from 'node:fs'
import { join } from 'node:path'
import { describe, expect, it } from 'vitest'
import { SAML_PROVIDERS_EXAMPLES, SSO_ICONS, SSO_NAMES, SSO_PROTOCOL, SSO_PROVIDERS, ssoSamlByHand, ssoSaveRequest, type SsoFormValues } from '../../shared/types/sso'
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

describe('the SAML tabs: Metadata address or Enter by hand (owner 2026-10-15)', () => {
  const saml = (metadata_url: string | null, entity_id: string | null) => ({ metadata_url, entity_id, sso_url: null, certificate: null })
  it('open a new Google Workspace connection on Enter by hand, a new SAML 2.0 one on the metadata address', () => {
    expect(ssoSamlByHand('google_workspace', null)).toBe(true)
    expect(ssoSamlByHand('saml', null)).toBe(false)
  })
  it('open a saved connection on the way it was saved', () => {
    expect(ssoSamlByHand('google_workspace', { provider: 'google_workspace', saml: saml('https://idp.example.com/metadata', null) })).toBe(false)
    expect(ssoSamlByHand('saml', { provider: 'saml', saml: saml(null, 'https://idp.example.com/entity') })).toBe(true)
    expect(ssoSamlByHand('saml', { provider: 'saml', saml: saml(null, null) })).toBe(false)
  })
  it('start a different choice on its own default, not the saved one', () => {
    const savedSaml = { provider: 'saml' as const, saml: saml('https://idp.example.com/metadata', null) }
    expect(ssoSamlByHand('google_workspace', savedSaml)).toBe(true)
  })
})

describe('what Save sends (only the chosen protocol, and for SAML only the active tab)', () => {
  // Every field filled, as if someone typed on both tabs before choosing
  const values: SsoFormValues = {
    label: ' Acme ', metadata_url: 'https://idp.example.com/metadata', entity_id: 'https://idp.example.com/entity', sso_url: 'https://idp.example.com/sso',
    certificate: '-----BEGIN CERTIFICATE-----\nMIIC\n-----END CERTIFICATE-----', issuer: 'https://login.microsoftonline.com/tenant/v2.0', client_id: 'app-id', client_secret: '',
    domains: ['example.com'], enforce: false, auto_create: true, default_role: 'member',
  }
  it('sends only the metadata address from the Metadata address tab', () => {
    const body = ssoSaveRequest('saml', false, values)
    expect(body.saml).toEqual({ metadata_url: 'https://idp.example.com/metadata', entity_id: null, sso_url: null, certificate: null })
    expect(body.oidc).toBeUndefined()
    expect(body.label).toBe('Acme')
  })
  it('sends only entity ID, sign-on address and certificate from Enter by hand', () => {
    const body = ssoSaveRequest('google_workspace', true, values)
    expect(body.saml).toEqual({ metadata_url: null, entity_id: values.entity_id, sso_url: values.sso_url, certificate: values.certificate })
    expect(body.oidc).toBeUndefined()
  })
  it('sends Entra ID\'s issuer and client ID, and a secret only when one is typed', () => {
    const kept = ssoSaveRequest('entra', true, values)
    expect(kept.saml).toBeUndefined()
    expect(kept.oidc).toEqual({ issuer: values.issuer, client_id: 'app-id' })
    expect(ssoSaveRequest('entra', false, { ...values, client_secret: 'new-secret' }).oidc).toEqual({ issuer: values.issuer, client_id: 'app-id', client_secret: 'new-secret' })
  })
  it('passes the save rules (the mock mirrors the backend) for every choice and tab', () => {
    for (const provider of SSO_PROVIDERS) for (const byHand of [false, true]) {
      const parsed = ssoSaveSchema.safeParse(ssoSaveRequest(provider, byHand, values))
      expect(parsed.success, `${provider} byHand=${byHand}`).toBe(true)
    }
  })
  it('leaves an empty field empty, which the server reads as not given', () => {
    const parsed = ssoSaveSchema.safeParse(ssoSaveRequest('saml', true, { ...values, sso_url: '', certificate: '' }))
    expect(parsed.success && parsed.data.saml).toMatchObject({ metadata_url: null, sso_url: null, certificate: null })
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
      // The two SAML tabs replace the link; the old link texts are gone
      for (const key of ['tabMetadata', 'tabByHand', 'googleByHand', 'idpSsoUrlHelp']) expect(sso[key], `${file} ${key}`).toBeTruthy()
      expect(sso.byHand, file).toBeUndefined()
      expect(sso.useMetadata, file).toBeUndefined()
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

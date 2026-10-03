import { describe, expect, it } from 'vitest'
import { API_KEY_PATTERN, ENDPOINT_PATTERN, apiEndpointUrl, formLink } from '../../shared/utils/urls/public'

const dev = { formsHost: 'forms.formalie.dev', rootDomain: 'formalie.dev', port: ':2202' }
const prod = { formsHost: 'forms.formalie.com', rootDomain: 'formalie.com' }

describe('public form links', () => {
  it('uses the shared forms host without a subdomain', () => {
    expect(formLink(prod, 'Kp3x9QmZ2a')).toBe('https://forms.formalie.com/Kp3x9QmZ2a/fill')
    expect(formLink(prod, 'Kp3x9QmZ2a', 'embed')).toBe('https://forms.formalie.com/Kp3x9QmZ2a/embed')
  })

  it('uses the workspace subdomain when it has one, with the dev port', () => {
    expect(formLink(prod, 'Kp3x9QmZ2a', 'fill', 'acme')).toBe('https://acme.formalie.com/Kp3x9QmZ2a/fill')
    expect(formLink(dev, 'Kp3x9QmZ2a', 'embed', 'acme')).toBe('https://acme.formalie.dev:2202/Kp3x9QmZ2a/embed')
    expect(formLink(dev, 'Kp3x9QmZ2a')).toBe('https://forms.formalie.dev:2202/Kp3x9QmZ2a/fill')
  })
})

describe('API service URLs', () => {
  it('builds short endpoint URLs', () => {
    expect(apiEndpointUrl('https://api.formalie.dev/', 'k7Qm2xP9aZ', 'register-account')).toBe(
      'https://api.formalie.dev/k7Qm2xP9aZ/register-account',
    )
    expect(apiEndpointUrl('https://api.formalie.com', 'k7Qm2xP9aZ', 'register-account', 'r_42')).toBe(
      'https://api.formalie.com/k7Qm2xP9aZ/register-account/r_42',
    )
  })

  it('validates keys and endpoint names', () => {
    expect(API_KEY_PATTERN.test('k7Qm2xP9aZ')).toBe(true)
    expect(API_KEY_PATTERN.test('hdhdhd46474fhfh4762')).toBe(false)
    expect(ENDPOINT_PATTERN.test('register-account')).toBe(true)
    expect(ENDPOINT_PATTERN.test('Register Account')).toBe(false)
    expect(ENDPOINT_PATTERN.test('-x-')).toBe(false)
  })
})

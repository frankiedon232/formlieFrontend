import { describe, expect, it } from 'vitest'
import { isValidSubdomain, normaliseHost, resolveHostContext } from '../../shared/utils/tenant/host'

const options = { rootDomain: 'formalie.dev', manageSubdomain: 'manage' }
const resolve = (host: string, tenantOverride?: string) =>
  resolveHostContext(host, { ...options, tenantOverride })

describe('normaliseHost', () => {
  it.each([
    ['Manage.Formalie.dev:2202', 'manage.formalie.dev'],
    ['formalie.dev.', 'formalie.dev'],
    ['[::1]:2202', '::1'],
    ['127.0.0.1:2202', '127.0.0.1'],
  ])('%s → %s', (input, expected) => expect(normaliseHost(input)).toBe(expected))
})

describe('resolveHostContext', () => {
  it('manage entry on manage., root and www', () => {
    expect(resolve('manage.formalie.dev:2202')).toMatchObject({ kind: 'manage', reason: 'manage' })
    expect(resolve('formalie.dev:2202')).toMatchObject({ kind: 'manage', reason: 'root' })
    expect(resolve('www.formalie.dev')).toMatchObject({ kind: 'manage', reason: 'root' })
  })

  it('tenant on its subdomain', () => {
    expect(resolve('remedylegal.formalie.dev:2202')).toEqual({
      kind: 'tenant',
      host: 'remedylegal.formalie.dev',
      subdomain: 'remedylegal',
    })
  })

  it('local hosts open the manage entry, or a tenant via override', () => {
    for (const host of ['localhost:2202', '127.0.0.1:2202', '[::1]:2202', '192.168.0.180:2202']) {
      expect(resolve(host)).toMatchObject({ kind: 'manage', reason: 'local' })
      expect(resolve(host, 'samathtax')).toMatchObject({ kind: 'tenant', subdomain: 'samathtax' })
    }
    expect(resolve('localhost', 'api')).toMatchObject({ kind: 'invalid', reason: 'reserved' })
  })

  it('*.localhost works without a hosts-file entry', () => {
    expect(resolve('acme.localhost:2202')).toMatchObject({ kind: 'tenant', subdomain: 'acme' })
    expect(resolve('manage.localhost:2202')).toMatchObject({ kind: 'manage', reason: 'manage' })
  })

  it('reserved, nested and malformed subdomains are invalid', () => {
    expect(resolve('api.formalie.dev')).toMatchObject({ kind: 'invalid', reason: 'reserved' })
    expect(resolve('forms.formalie.dev')).toMatchObject({ kind: 'invalid', reason: 'reserved' })
    expect(resolve('a.b.formalie.dev')).toMatchObject({ kind: 'invalid', reason: 'nested' })
    expect(resolve('-bad-.formalie.dev')).toMatchObject({ kind: 'invalid', reason: 'malformed' })
  })

  it('other domains are custom domains', () => {
    expect(resolve('forms.customer.com')).toEqual({ kind: 'custom', host: 'forms.customer.com' })
  })
})

describe('isValidSubdomain', () => {
  it('accepts normal names and rejects reserved / malformed', () => {
    expect(isValidSubdomain('remedylegal')).toBe(true)
    expect(isValidSubdomain('samath-tax2')).toBe(true)
    expect(isValidSubdomain('admin')).toBe(false)
    expect(isValidSubdomain('Bad_Name')).toBe(false)
    expect(isValidSubdomain('-x')).toBe(false)
  })
})

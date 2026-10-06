import { describe, expect, it } from 'vitest'
import { checkHeaderName, checkHeaderValue, maskValue, scopeAllows, secretPreview, tokenPrefix, tokenStatusOf } from '../../shared/utils/apiService/tokens'

const DAY = 86_400_000

describe('token secrets', () => {
  it('tells live and test apart by prefix', () => {
    expect(tokenPrefix('static', 'live')).toBe('fml_live_')
    expect(tokenPrefix('client', 'test')).toBe('fcs_test_')
    expect(tokenPrefix('client_id', 'live')).toBe('cli_live_')
    expect(tokenPrefix('signing', 'test')).toBe('fsg_test_')
  })

  it('shows only the prefix and the last 4 characters', () => {
    expect(secretPreview('fml_live_abcdefghijklmnopqrstuvwxyz123456')).toBe('fml_live_…3456')
    expect(maskValue('partner-42')).toBe('••••r-42')
    expect(maskValue('abc')).toBe('••••')
  })
})

describe('token status', () => {
  const now = Date.parse('2026-10-06T12:00:00Z')
  it('reads revoked, expired, expiring and active from the dates', () => {
    expect(tokenStatusOf({ revoked_at: '2026-10-01T00:00:00Z', expires_at: null }, now)).toBe('revoked')
    expect(tokenStatusOf({ revoked_at: null, expires_at: new Date(now - DAY).toISOString() }, now)).toBe('expired')
    expect(tokenStatusOf({ revoked_at: null, expires_at: new Date(now + 5 * DAY).toISOString() }, now)).toBe('expiring')
    expect(tokenStatusOf({ revoked_at: null, expires_at: new Date(now + 60 * DAY).toISOString() }, now)).toBe('active')
    expect(tokenStatusOf({ revoked_at: null, expires_at: null }, now)).toBe('active')
  })
})

describe('scopes', () => {
  const target = { endpoint_id: 'e1', service_id: 's1', method: 'POST' as const }
  it('allows everything when the lists are empty', () => {
    expect(scopeAllows({ services: [], endpoints: [], methods: [] }, target)).toBe(true)
  })
  it('limits by service, endpoint and method', () => {
    expect(scopeAllows({ services: ['s2'], endpoints: [], methods: [] }, target)).toBe(false)
    expect(scopeAllows({ services: ['s1'], endpoints: ['e2'], methods: [] }, target)).toBe(false)
    expect(scopeAllows({ services: ['s1'], endpoints: [], methods: ['GET'] }, target)).toBe(false)
    expect(scopeAllows({ services: ['s1'], endpoints: ['e1'], methods: ['POST', 'GET'] }, target)).toBe(true)
  })
})

describe('required headers', () => {
  it('accepts custom names, refuses ones HTTP or Formalie set', () => {
    expect(checkHeaderName('X-Partner-Id')).toBeNull()
    expect(checkHeaderName('')).toBe('required')
    expect(checkHeaderName('1abc')).toBe('pattern')
    expect(checkHeaderName('Bad Name')).toBe('pattern')
    expect(checkHeaderName('Authorization')).toBe('reserved')
    expect(checkHeaderName('content-type')).toBe('reserved')
    expect(checkHeaderName('X-Formalie-Anything')).toBe('reserved')
  })
  it('wants a printable value of up to 200 characters', () => {
    expect(checkHeaderValue('acme-42')).toBeNull()
    expect(checkHeaderValue('')).toBe('required')
    expect(checkHeaderValue(' leading')).toBe('chars')
    expect(checkHeaderValue('é')).toBe('chars')
    expect(checkHeaderValue('x'.repeat(201))).toBe('chars')
  })
})

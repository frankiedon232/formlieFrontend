import { describe, expect, it } from 'vitest'
import { checkRuleValue, decideAccess, ipInCidr, normaliseRuleValue, parseIp, REGIONS, regionOf, rulesFor } from '../../shared/utils/apiService/access'
import { COUNTRY_CODES } from '../../shared/utils/platform/countries'

const caller = (ip: string, domain: string | null = null, country: string | null = null) => ({ ip, domain, country })
const rule = (id: string, action: 'allow' | 'block', kind: 'ip' | 'domain' | 'country' | 'region', values: string[], enabled = true) => ({ id, action, kind, values, enabled })

describe('IP addresses and ranges', () => {
  it('reads IPv4, IPv6 and mapped addresses', () => {
    expect(parseIp('203.0.113.10')?.family).toBe(4)
    expect(parseIp('2001:db8::1')?.family).toBe(6)
    expect(parseIp('::ffff:127.0.0.1')?.family).toBe(4)
    expect(parseIp('256.1.1.1')).toBeNull()
    expect(parseIp('not-an-ip')).toBeNull()
  })
  it('matches addresses inside a range only', () => {
    expect(ipInCidr('198.51.100.7', '198.51.100.0/28')).toBe(true)
    expect(ipInCidr('198.51.100.20', '198.51.100.0/28')).toBe(false)
    expect(ipInCidr('203.0.113.10', '203.0.113.10')).toBe(true)
    expect(ipInCidr('2001:db8::abcd', '2001:db8::/32')).toBe(true)
    expect(ipInCidr('2001:db9::1', '2001:db8::/32')).toBe(false)
    expect(ipInCidr('203.0.113.10', '2001:db8::/32')).toBe(false)
  })
})

describe('rule values', () => {
  it('checks each kind', () => {
    expect(checkRuleValue('ip', '198.51.100.0/24')).toBeNull()
    expect(checkRuleValue('ip', '198.51.100.0/33')).toBe('ip')
    expect(checkRuleValue('domain', '*.example.com')).toBeNull()
    expect(checkRuleValue('domain', 'not a domain')).toBe('domain')
    expect(checkRuleValue('country', 'gb')).toBeNull()
    expect(checkRuleValue('country', 'ZZ')).toBe('country')
    expect(checkRuleValue('region', 'eu')).toBeNull()
    expect(checkRuleValue('region', 'XX')).toBe('region')
    expect(checkRuleValue('ip', ' ')).toBe('required')
  })
  it('stores domains in lower case, countries and regions in upper case', () => {
    expect(normaliseRuleValue('domain', ' WWW.Example.com ')).toBe('www.example.com')
    expect(normaliseRuleValue('country', 'ng')).toBe('NG')
  })
  it('puts every country in exactly one region', () => {
    const placed = Object.values(REGIONS).flat()
    expect(new Set(placed).size).toBe(placed.length)
    const missing = COUNTRY_CODES.filter(code => !placed.includes(code) && code !== 'AQ')
    expect(missing).toEqual([])
    expect(regionOf('KE')).toBe('AF')
    expect(regionOf('BR')).toBe('SA')
  })
})

describe('the decision', () => {
  it('lets everyone in without rules', () => {
    expect(decideAccess([], caller('203.0.113.10'))).toMatchObject({ allowed: true, reason: null })
  })
  it('refuses on a matching block, even when an allow rule matches too', () => {
    const decision = decideAccess([rule('a', 'allow', 'ip', ['203.0.113.0/24']), rule('b', 'block', 'ip', ['203.0.113.10'])], caller('203.0.113.10'))
    expect(decision).toMatchObject({ allowed: false, reason: 'blocked', rule: { id: 'b', value: '203.0.113.10' } })
  })
  it('requires a matching allow rule once allow rules apply', () => {
    const rules = [rule('a', 'allow', 'country', ['GB'])]
    expect(decideAccess(rules, caller('203.0.113.10', null, 'GB')).allowed).toBe(true)
    expect(decideAccess(rules, caller('203.0.113.10', null, 'FR'))).toMatchObject({ allowed: false, reason: 'not_allowed' })
  })
  it('matches domains from browsers only, wildcards for subdomains', () => {
    const rules = [rule('a', 'allow', 'domain', ['*.example.com'])]
    expect(decideAccess(rules, caller('1.1.1.1', 'shop.example.com')).allowed).toBe(true)
    expect(decideAccess(rules, caller('1.1.1.1', 'example.com')).allowed).toBe(false)
    expect(decideAccess(rules, caller('1.1.1.1', null)).allowed).toBe(false)
  })
  it('ignores rules that are switched off, and regions follow the country', () => {
    expect(decideAccess([rule('a', 'block', 'region', ['EU'], false)], caller('1.1.1.1', null, 'DE')).allowed).toBe(true)
    expect(decideAccess([rule('a', 'block', 'region', ['EU'])], caller('1.1.1.1', null, 'DE')).allowed).toBe(false)
  })
  it('applies rules for everything, the endpoint\'s service and the endpoint itself', () => {
    const rules = [
      { id: '1', scope: { type: 'all', id: null } },
      { id: '2', scope: { type: 'service', id: 's1' } },
      { id: '3', scope: { type: 'service', id: 's2' } },
      { id: '4', scope: { type: 'endpoint', id: 'e1' } },
      { id: '5', scope: { type: 'endpoint', id: 'e2' } },
    ]
    expect(rulesFor(rules, { id: 'e1', service_id: 's1' }).map(item => item.id)).toEqual(['1', '2', '4'])
  })
})

describe('anonymous networks', () => {
  it('take only the known networks', () => {
    expect(checkRuleValue('network', 'vpn')).toBeNull()
    expect(checkRuleValue('network', 'TOR')).toBeNull()
    expect(checkRuleValue('network', 'satellite')).toBe('network')
    expect(normaliseRuleValue('network', ' Hosting ')).toBe('hosting')
  })

  it('block callers whose address belongs to one, whatever their country', () => {
    const rules = [{ id: 'n', action: 'block' as const, kind: 'network' as const, values: ['vpn', 'tor'], enabled: true }]
    expect(decideAccess(rules, { ip: '203.0.113.9', domain: null, country: 'GB', networks: ['vpn'] })).toMatchObject({ allowed: false, reason: 'blocked', rule: { value: 'vpn' } })
    expect(decideAccess(rules, { ip: '203.0.113.9', domain: null, country: 'GB', networks: ['hosting'] }).allowed).toBe(true)
    expect(decideAccess(rules, { ip: '203.0.113.9', domain: null, country: 'GB' }).allowed).toBe(true)
  })
})

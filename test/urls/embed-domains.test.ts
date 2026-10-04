import { describe, expect, it } from 'vitest'
import { frameAncestors, normaliseEmbedDomain } from '../../shared/utils/urls/embed-domains'

describe('embed websites', () => {
  it('turns what people paste into a host', () => {
    expect(normaliseEmbedDomain('https://www.Example.com/contact?x=1')).toBe('example.com')
    expect(normaliseEmbedDomain('*.example.org')).toBe('*.example.org')
    expect(normaliseEmbedDomain('shop.example.co.uk')).toBe('shop.example.co.uk')
    expect(normaliseEmbedDomain('localhost:3000')).toBe('localhost:3000')
    expect(normaliseEmbedDomain('not a site')).toBeNull()
    expect(normaliseEmbedDomain('example')).toBeNull()
    expect(normaliseEmbedDomain('example.com:abc')).toBeNull()
  })

  it('builds the frame-ancestors rule', () => {
    expect(frameAncestors([], 'formalie.com')).toBe('*')
    const rule = frameAncestors(['example.com', '*.shop.org', 'localhost:3000'], 'formalie.com')
    expect(rule).toContain("'self'")
    expect(rule).toContain('https://*.formalie.com')
    expect(rule).toContain('https://example.com https://www.example.com')
    expect(rule).toContain('https://*.shop.org')
    expect(rule).not.toContain('www.*.shop.org')
    expect(rule).toContain('http://localhost:3000')
  })
})

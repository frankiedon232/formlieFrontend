import { describe, expect, it } from 'vitest'
import { normaliseOrigin, originAllowed } from '../../shared/utils/apiService/origins'

describe('API service allowed websites (leftovers L6)', () => {
  it('keeps websites in one form', () => {
    expect(normaliseOrigin('https://Shop.Example.com/')).toBe('https://shop.example.com')
    expect(normaliseOrigin('shop.example.com')).toBe('https://shop.example.com')
    expect(normaliseOrigin('https://shop.example.com:8443')).toBe('https://shop.example.com:8443')
    expect(normaliseOrigin('http://localhost:3000')).toBe('http://localhost:3000')
  })

  it('refuses pages, plain http and things that are not websites', () => {
    expect(normaliseOrigin('https://shop.example.com/checkout')).toBeNull()
    expect(normaliseOrigin('http://shop.example.com')).toBeNull()
    expect(normaliseOrigin('https://shop.example.com?x=1')).toBeNull()
    expect(normaliseOrigin('https://user:pw@shop.example.com')).toBeNull()
    expect(normaliseOrigin('*')).toBeNull()
    expect(normaliseOrigin('javascript:alert(1)')).toBeNull()
    expect(normaliseOrigin('https://intranet')).toBeNull()
  })

  it('allows only the listed websites', () => {
    const allowed = ['https://shop.example.com']
    expect(originAllowed('https://shop.example.com', allowed)).toBe(true)
    expect(originAllowed('https://SHOP.example.com', allowed)).toBe(true)
    expect(originAllowed('https://evil.example.com', allowed)).toBe(false)
    expect(originAllowed('https://shop.example.com.evil.example', allowed)).toBe(false)
    expect(originAllowed(null, allowed)).toBe(false)
    expect(originAllowed('https://shop.example.com', [])).toBe(false)
  })
})

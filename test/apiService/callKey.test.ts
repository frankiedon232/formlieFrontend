import { describe, expect, it } from 'vitest'
import { canonicalJson, checkCallKey } from '../../shared/utils/apiService/tokens'

describe('Formalie-Key', () => {
  it('takes a UUID and other long random ids', () => {
    expect(checkCallKey('6f1c2a90-3d4b-4e8f-9a17-0c5d2b7e8f41')).toBeNull()
    expect(checkCallKey('order_2026-10-06_x7Qm9Lp2')).toBeNull()
  })

  it('says what is wrong with the rest', () => {
    expect(checkCallKey('')).toBe('missing')
    expect(checkCallKey('has spaces in it, sixteen+')).toBe('invalid')
    expect(checkCallKey('x'.repeat(101))).toBe('invalid')
    expect(checkCallKey('1234567890')).toBe('short')
    expect(checkCallKey('abc12345')).toBe('short')
    expect(checkCallKey('1111111111111111')).toBe('weak')
    expect(checkCallKey('abababababababab')).toBe('weak')
    expect(checkCallKey('aaaa1111bbbb2222')).toBe('weak')
    expect(checkCallKey('1234567890123456')).toBe('weak')
    expect(checkCallKey('zyxwvutsrqponmlk')).toBe('weak')
  })
})

describe('same request', () => {
  it('is recognised whatever the order of the keys', () => {
    expect(canonicalJson({ b: 1, a: { d: [2, { y: 1, x: 0 }], c: null } })).toBe(canonicalJson({ a: { c: null, d: [2, { x: 0, y: 1 }] }, b: 1 }))
    expect(canonicalJson({ a: 1 })).not.toBe(canonicalJson({ a: 2 }))
  })
})

import { describe, expect, it } from 'vitest'
import type { FormField } from '../../shared/utils/forms/build'
import { validateAnswer } from '../../shared/utils/forms/validate'

const field = (type: string, extra: Partial<FormField> = {}) => ({ id: 'f', key: 'k', type, label: 'Field', ...extra }) as FormField
const code = (f: FormField, value: unknown, required = false) => validateAnswer(f, value, required)?.code ?? null

describe('answer validation', () => {
  it('checks emails, links and phone numbers', () => {
    expect(code(field('email'), 'name@example.com')).toBeNull()
    expect(code(field('email'), 'hello')).toBe('email')
    expect(code(field('email'), 'a@b')).toBe('email')
    expect(code(field('url'), 'https://example.org/page')).toBeNull()
    expect(code(field('url'), 'example')).toBe('url')
    expect(code(field('url'), 'javascript:alert(1)')).toBe('url')
    expect(code(field('phone'), '+44 7700 900123')).toBeNull()
    expect(code(field('phone'), 'call me')).toBe('phone')
  })

  it('checks required, numbers, length, pattern and choices', () => {
    expect(code(field('short_text'), '', true)).toBe('required')
    expect(code(field('short_text'), '', false)).toBeNull()
    expect(code(field('number', { validation: { min: 1, max: 5 } }), 9)).toBe('max')
    expect(code(field('number'), 'abc')).toBe('number')
    expect(code(field('short_text', { validation: { min_length: 3 } }), 'ab')).toBe('min_length')
    expect(code(field('short_text', { validation: { pattern: '^[A-Z]{2}[0-9]+$' } }), 'ab12')).toBe('pattern')
    expect(code(field('checkbox', { validation: { min_selected: 2 } }), ['a'])).toBe('min_selected')
    expect(code(field('rich_text', { validation: { max_length: 3 } }), '<p><strong>abcd</strong></p>')).toBe('max_length')
    expect(code(field('rich_text'), '<p></p>', true)).toBe('required')
  })

  it('checks every required part of an address', () => {
    const address = field('address')
    expect(code(address, { line1: '1 Main Street' }, true)).toBe('address')
    expect(validateAnswer(address, { line1: '1 Main Street' }, true)?.parts).toEqual(['city', 'postal_code', 'country'])
    expect(code(address, { line1: 'x', city: 'y', postal_code: 'z', country: 'GB' }, true)).toBeNull()
    expect(code(field('address', { props: { require_postal_code: false } }), { line1: 'x', city: 'y', country: 'AE' }, true)).toBeNull()
    expect(validateAnswer(field('address', { props: { require_region: true } }), { line1: 'x', city: 'y', postal_code: 'z', country: 'GB' }, true)?.parts).toEqual(['region'])
    // An optional address that was started must still be complete.
    expect(code(address, { city: 'y' }, false)).toBe('address')
    expect(code(address, {}, false)).toBeNull()
  })

  it('checks date ranges', () => {
    expect(code(field('date_range'), { from: '2026-10-05', to: '2026-10-01' })).toBe('date_range')
    expect(code(field('date_range'), { from: '2026-10-01', to: '' })).toBe('date_range')
    expect(code(field('date_range'), { from: '2026-10-01', to: '2026-10-05' })).toBeNull()
  })
})

describe('technical and global fields', () => {
  it('checks IP addresses, domains, MAC addresses', () => {
    expect(code(field('ip_address'), '192.0.2.10')).toBeNull()
    expect(code(field('ip_address'), '2001:db8::1')).toBeNull()
    expect(code(field('ip_address'), '::ffff:192.0.2.1')).toBeNull()
    expect(code(field('ip_address'), '256.1.1.1')).toBe('ip')
    expect(code(field('ip_address', { props: { ip_version: 'v4' } }), '2001:db8::1')).toBe('ip')
    expect(code(field('ip_address', { props: { ip_version: 'v6' } }), '192.0.2.10')).toBe('ip')
    expect(code(field('domain'), 'sub.example.org')).toBeNull()
    expect(code(field('domain'), 'not a domain')).toBe('domain')
    expect(code(field('mac_address'), '00:1A:2B:3C:4D:5E')).toBeNull()
    expect(code(field('mac_address'), '00:1A:2B')).toBe('mac')
  })

  it('checks IBAN, BIC, colours, percentages', () => {
    expect(code(field('iban'), 'GB82 WEST 1234 5698 7654 32')).toBeNull()
    expect(code(field('iban'), 'GB82 WEST 1234 5698 7654 33')).toBe('iban')
    expect(code(field('bic'), 'ABCDGB2LXXX')).toBeNull()
    expect(code(field('bic'), 'AB12')).toBe('bic')
    expect(code(field('color'), '#1a2b3c')).toBeNull()
    expect(code(field('color'), 'blue')).toBe('color')
    expect(code(field('percentage', { validation: { min: 0, max: 100 } }), 120)).toBe('max')
  })

  it('checks names, consent, durations and picks', () => {
    expect(code(field('full_name'), { first: 'Ada' }, true)).toBe('name')
    expect(code(field('full_name'), { first: 'Ada', last: 'Okafor' }, true)).toBeNull()
    expect(code(field('consent'), false, true)).toBe('consent')
    expect(code(field('consent'), true, true)).toBeNull()
    expect(code(field('duration'), { hours: 1, minutes: 75 })).toBe('duration')
    expect(code(field('duration'), { hours: 1, minutes: 30 })).toBeNull()
    expect(code(field('language'), 'sw')).toBeNull()
    expect(code(field('language'), 'xx')).toBe('choice')
    expect(code(field('timezone'), 'Asia/Kolkata')).toBeNull()
    expect(code(field('timezone'), 'Mars/Base')).toBe('choice')
  })
})

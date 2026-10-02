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

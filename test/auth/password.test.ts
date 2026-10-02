import { describe, expect, it } from 'vitest'
import { checkPassword, meetsPasswordPolicy, passwordScore } from '../../shared/utils/auth/password'

describe('password policy', () => {
  it('scores from empty to strong', () => {
    expect(passwordScore('')).toBe(0)
    expect(passwordScore('abc')).toBe(1)
    expect(passwordScore('abcdefghij1')).toBe(2)
    expect(passwordScore('Abcdefghij1')).toBe(3)
    expect(passwordScore('Abcdefghij1!')).toBe(4)
    expect(passwordScore('Abcdefghijklmn1')).toBe(4)
  })

  it('requires length, lower, upper and a number; symbols are optional', () => {
    expect(meetsPasswordPolicy('Formalie!2026')).toBe(true)
    expect(meetsPasswordPolicy('Formalie2026')).toBe(true)
    expect(meetsPasswordPolicy('formalie2026')).toBe(false)
    expect(meetsPasswordPolicy('Short1')).toBe(false)
    expect(checkPassword('x').find(c => c.key === 'symbol')?.required).toBe(false)
  })
})

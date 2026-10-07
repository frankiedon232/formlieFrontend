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

describe('workspace password rules', () => {
  const strict = { min_length: 14, lower: true, upper: true, number: true, symbol: true }
  const relaxed = { min_length: 8, lower: true, upper: false, number: false, symbol: false }

  it('follow the workspace rules', () => {
    expect(meetsPasswordPolicy('Abcdefghij1', strict)).toBe(false)
    expect(meetsPasswordPolicy('Abcdefghijkl1!', strict)).toBe(true)
    expect(meetsPasswordPolicy('lowercase', relaxed)).toBe(true)
    expect(checkPassword('Abcdefghijkl1', strict).find(check => check.key === 'symbol')).toMatchObject({ required: true, passed: false })
  })

  it('score against the same rules', () => {
    expect(passwordScore('Abcdefghijkl1', strict)).toBe(1)
    expect(passwordScore('Abcdefghijklm1', strict)).toBe(2)
    expect(passwordScore('Abcdefghijkl1!', strict)).toBe(4)
  })
})

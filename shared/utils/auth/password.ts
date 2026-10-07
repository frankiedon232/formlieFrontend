/**
 * Password policy shared by the signup / reset forms and the mock API (FRM-AUTH-1007). Each workspace
 * sets its own in Settings → Security (F14 M3); the default: ≥ 10 characters, lower + upper case, a
 * number. Symbols raise the score when they aren't required.
 */
import type { PasswordPolicy } from '../../types/auth'

export const PASSWORD_MIN_LENGTH = 10
export const DEFAULT_PASSWORD_POLICY: PasswordPolicy = { min_length: PASSWORD_MIN_LENGTH, lower: true, upper: true, number: true, symbol: false }
/** The range Settings offers for the minimum length. */
export const PASSWORD_LENGTH_RANGE = { min: 8, max: 64 } as const

export interface PasswordCheck {
  key: 'length' | 'lower' | 'upper' | 'number' | 'symbol'
  passed: boolean
  required: boolean
}

export function checkPassword(value: string, policy: PasswordPolicy = DEFAULT_PASSWORD_POLICY): PasswordCheck[] {
  return [
    { key: 'length', passed: value.length >= policy.min_length, required: true },
    { key: 'lower', passed: /[a-z]/.test(value), required: policy.lower },
    { key: 'upper', passed: /[A-Z]/.test(value), required: policy.upper },
    { key: 'number', passed: /\d/.test(value), required: policy.number },
    { key: 'symbol', passed: /[^A-Za-z0-9]/.test(value), required: policy.symbol },
  ]
}

/** 0 (empty) … 4 (strong). Meets the policy at 3. */
export function passwordScore(value: string, policy: PasswordPolicy = DEFAULT_PASSWORD_POLICY): 0 | 1 | 2 | 3 | 4 {
  if (!value) return 0
  const checks = checkPassword(value, policy)
  const required = checks.filter(check => check.required)
  if (!required.every(check => check.passed)) return required.filter(check => check.passed).length >= Math.max(1, required.length - 1) ? 2 : 1
  const kinds = checks.filter(check => check.key !== 'length' && check.passed).length
  return value.length >= Math.max(14, policy.min_length + 4) || kinds === 4 ? 4 : 3
}

export const meetsPasswordPolicy = (value: string, policy: PasswordPolicy = DEFAULT_PASSWORD_POLICY) => checkPassword(value, policy).every(check => !check.required || check.passed)

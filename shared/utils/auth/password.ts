/**
 * Password policy shared by the signup / reset forms and the mock API (FRM-AUTH-1007).
 * Default tenant policy: ≥ 10 characters, lower + upper case, a number. Symbols raise the score.
 */
export const PASSWORD_MIN_LENGTH = 10

export interface PasswordCheck {
  key: 'length' | 'lower' | 'upper' | 'number' | 'symbol'
  passed: boolean
  required: boolean
}

export function checkPassword(value: string): PasswordCheck[] {
  return [
    { key: 'length', passed: value.length >= PASSWORD_MIN_LENGTH, required: true },
    { key: 'lower', passed: /[a-z]/.test(value), required: true },
    { key: 'upper', passed: /[A-Z]/.test(value), required: true },
    { key: 'number', passed: /\d/.test(value), required: true },
    { key: 'symbol', passed: /[^A-Za-z0-9]/.test(value), required: false },
  ]
}

/** 0 (empty) … 4 (strong). Meets the policy at 3. */
export function passwordScore(value: string): 0 | 1 | 2 | 3 | 4 {
  if (!value) return 0
  const checks = checkPassword(value)
  const required = checks.filter(check => check.required)
  if (!required.every(check => check.passed))
    return required.filter(check => check.passed).length >= 3 ? 2 : 1
  const long = value.length >= 14
  return checks.find(check => check.key === 'symbol')!.passed || long ? 4 : 3
}

export const meetsPasswordPolicy = (value: string) =>
  checkPassword(value).every(check => !check.required || check.passed)

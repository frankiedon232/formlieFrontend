import { describe, expect, it } from 'vitest'
import { customLinkProblem, isFormAddress, tidyCustomLink } from '../../shared/utils/urls/public'

describe('custom links', () => {
  it('accepts readable links and refuses the rest', () => {
    expect(customLinkProblem('procurement-request')).toBeNull()
    expect(customLinkProblem('a1b')).toBeNull()
    expect(customLinkProblem('ab')).toBe('invalid')
    expect(customLinkProblem('Bad-Case')).toBe('invalid')
    expect(customLinkProblem('double--hyphen')).toBe('invalid')
    expect(customLinkProblem('-start')).toBe('invalid')
    expect(customLinkProblem('forms')).toBe('reserved')
    expect(customLinkProblem('settings')).toBe('reserved')
  })

  it('tidies what people type', () => {
    expect(tidyCustomLink('  Procurement Request 2026! ')).toBe('procurement-request-2026')
    expect(tidyCustomLink('Café Évènement')).toBe('cafe-evenement')
  })

  it('public pages accept a key or a custom link', () => {
    expect(isFormAddress('Ab3dEf7hJk')).toBe(true)
    expect(isFormAddress('procurement-request')).toBe(true)
    expect(isFormAddress('Not A Link')).toBe(false)
  })
})

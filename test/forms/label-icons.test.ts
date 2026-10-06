import { describe, expect, it } from 'vitest'
import { iconFromLabel } from '../../shared/utils/forms/label-icons'

describe('icons from labels', () => {
  it('reads the meaning of common labels', () => {
    expect(iconFromLabel('First Name')).toBe('i-lucide-user')
    expect(iconFromLabel('Company name')).toBe('i-lucide-building-2')
    expect(iconFromLabel('Product name')).toBe('i-lucide-package')
    expect(iconFromLabel('City')).toBe('i-lucide-building')
    expect(iconFromLabel('Zipcode')).toBe('i-lucide-mailbox')
    expect(iconFromLabel('Date of birth')).toBe('i-lucide-cake')
    expect(iconFromLabel('Expected yearly salary')).toBe('i-lucide-banknote')
    expect(iconFromLabel('Why would you like to join us?')).toBe('i-lucide-message-square')
    expect(iconFromLabel('LinkedIn or portfolio')).toBe('i-lucide-globe')
    expect(iconFromLabel('Phone number')).toBe('i-lucide-phone')
  })

  it('works in other languages and with accents', () => {
    expect(iconFromLabel('Prénom')).toBe('i-lucide-user')
    expect(iconFromLabel('Teléfono')).toBe('i-lucide-phone')
    expect(iconFromLabel('Código postal')).toBe('i-lucide-mailbox')
    expect(iconFromLabel('Stadt')).toBe('i-lucide-building')
  })

  it('matches whole words only and falls back to nothing', () => {
    expect(iconFromLabel('Personal data processing')).toBeNull()
    expect(iconFromLabel('Catalogue')).toBeNull()
    expect(iconFromLabel('')).toBeNull()
    expect(iconFromLabel('Something', 'first_name_w6r3')).toBe('i-lucide-user')
  })
})

describe('more labels', () => {
  it('cover questions and common business words', () => {
    expect(iconFromLabel('What could we do better?')).toBe('i-lucide-message-square')
    expect(iconFromLabel('When did it happen?')).toBe('i-lucide-calendar')
    expect(iconFromLabel('Where did it happen?')).toBe('i-lucide-map-pin')
    expect(iconFromLabel('Campaign source')).toBe('i-lucide-megaphone')
    expect(iconFromLabel('Review priority')).toBe('i-lucide-signal-high')
    expect(iconFromLabel('Accessibility needs')).toBe('i-lucide-accessibility')
    expect(iconFromLabel('Subtotal')).toBe('i-lucide-banknote')
    expect(iconFromLabel('Reported by')).toBe('i-lucide-user-round-check')
  })
})

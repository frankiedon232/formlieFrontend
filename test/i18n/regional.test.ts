import { describe, expect, it } from 'vitest'
import {
  formatDatePattern,
  formatNumberPattern,
  suggestDateFormat,
  suggestNumberFormat,
  suggestWeekStart,
} from '../../app/utils/i18n/regional'
import { COUNTRY_CODES, COUNTRY_CURRENCIES, CURRENCY_CODES } from '../../shared/utils/platform/countries'

describe('platform countries', () => {
  it('lists every country once with an ISO currency', () => {
    expect(COUNTRY_CODES.length).toBeGreaterThan(240)
    expect(new Set(COUNTRY_CODES).size).toBe(COUNTRY_CODES.length)
    for (const code of COUNTRY_CODES) {
      expect(code).toMatch(/^[A-Z]{2}$/)
      expect(COUNTRY_CURRENCIES[code]).toMatch(/^[A-Z]{3}$/)
    }
    expect(COUNTRY_CURRENCIES.PT).toBe('EUR')
    expect(COUNTRY_CURRENCIES.JP).toBe('JPY')
    expect(CURRENCY_CODES).toContain('USD')
  })

  it('every currency is known to Intl', () => {
    const supported = new Set(Intl.supportedValuesOf('currency'))
    // Very new codes may be missing from older ICU data; allow those explicitly.
    const unknown = CURRENCY_CODES.filter(
      code => !supported.has(code) && !['ZWG', 'SLE', 'VES'].includes(code),
    )
    expect(unknown).toEqual([])
  })
})

describe('regional patterns', () => {
  const date = new Date(Date.UTC(2026, 9, 2, 12))

  it('formats dates with each pattern', () => {
    expect(formatDatePattern(date, 'DD/MM/YYYY', 'UTC')).toBe('02/10/2026')
    expect(formatDatePattern(date, 'MM/DD/YYYY', 'UTC')).toBe('10/02/2026')
    expect(formatDatePattern(date, 'YYYY-MM-DD', 'UTC')).toBe('2026-10-02')
    expect(formatDatePattern(date, 'DD.MM.YYYY', 'UTC')).toBe('02.10.2026')
  })

  it('respects the timezone for the calendar day', () => {
    const lateUtc = new Date(Date.UTC(2026, 9, 2, 23, 30))
    expect(formatDatePattern(lateUtc, 'YYYY-MM-DD', 'Asia/Tokyo')).toBe('2026-10-03')
  })

  it('formats numbers with each separator style', () => {
    expect(formatNumberPattern(1234567.891, '1,234.56')).toBe('1,234,567.89')
    expect(formatNumberPattern(1234567.891, '1.234,56')).toBe('1.234.567,89')
    expect(formatNumberPattern(1234567.891, '1 234,56')).toBe('1 234 567,89')
    expect(formatNumberPattern(-1234.5, "1'234.56")).toBe("-1'234.50")
    expect(formatNumberPattern(12, '1,234.56', 0)).toBe('12')
  })

  it('suggests sensible defaults per country', () => {
    expect(suggestDateFormat('US')).toBe('MM/DD/YYYY')
    expect(suggestDateFormat('DE')).toBe('DD.MM.YYYY')
    expect(suggestDateFormat('JP')).toBe('YYYY-MM-DD')
    expect(suggestDateFormat(null)).toBe('DD/MM/YYYY')
    expect(suggestNumberFormat('DE')).toBe('1.234,56')
    expect(suggestNumberFormat('FR')).toBe('1 234,56')
    expect(suggestNumberFormat('CH')).toBe("1'234.56")
    expect(suggestWeekStart('US')).toBe('sunday')
    expect(suggestWeekStart('AE')).toBe('saturday')
    expect(suggestWeekStart('GB')).toBe('monday')
  })
})

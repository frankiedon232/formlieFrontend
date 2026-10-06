import { describe, expect, it } from 'vitest'
import { brandingSchema, companySchema, isTimeZone, localisationSchema } from '../../shared/utils/settings/schemas'

const company = {
  legal_name: 'Northwind Trading Ltd.',
  display_name: 'Northwind',
  industry: 'retail',
  size: '11-50',
  website: 'https://northwind.example',
  registration_number: '',
  tax_number: null,
  support_email: 'help@northwind.example',
  support_phone: '+44 7700 900123',
  address: { line1: '1 Example Street', line2: '', city: 'Sample City', region: null, postal_code: '10115', country: 'GB' },
}

describe('company settings', () => {
  it('take a full record and turn empty texts into null', () => {
    const result = companySchema.parse(company)
    expect(result.registration_number).toBeNull()
    expect(result.address.line2).toBeNull()
    expect(result.display_name).toBe('Northwind')
  })

  it('say which field is wrong', () => {
    const result = companySchema.safeParse({ ...company, website: 'northwind', support_email: 'help@', support_phone: 'call me', address: { ...company.address, country: 'XX' } })
    expect(result.success).toBe(false)
    const fields = Object.fromEntries((result.error?.issues ?? []).map(issue => [issue.path.join('.'), issue.message]))
    expect(fields).toMatchObject({ website: 'website', support_email: 'email', support_phone: 'phone', 'address.country': 'country' })
  })

  it('need both names', () => {
    expect(companySchema.safeParse({ ...company, display_name: ' ' }).success).toBe(false)
  })
})

describe('branding settings', () => {
  it('keep, replace or remove each picture', () => {
    expect(brandingSchema.parse({ brand_color: '#2563eb', signin_message: '' })).toMatchObject({ brand_color: '#2563eb', signin_message: null })
    expect(brandingSchema.parse({ logo_upload_id: null, favicon_upload_id: 'up_1', brand_color: null, signin_message: 'Welcome' })).toMatchObject({ logo_upload_id: null, favicon_upload_id: 'up_1' })
  })

  it('refuse a colour that is not #RRGGBB', () => {
    expect(brandingSchema.safeParse({ brand_color: 'blue', signin_message: null }).success).toBe(false)
  })
})

describe('language and region', () => {
  const localisation = { language: 'en', timezone: 'Europe/London', currency: 'EUR', date_format: 'YYYY-MM-DD', number_format: '1.234,56', week_start: 'monday', form_languages: ['en', 'fr'] }

  it('take a real time zone and currency', () => {
    expect(localisationSchema.safeParse(localisation).success).toBe(true)
    expect(isTimeZone('UTC')).toBe(true)
    expect(isTimeZone('Mars/Olympus')).toBe(false)
  })

  it('keep at least one language for forms', () => {
    const result = localisationSchema.safeParse({ ...localisation, form_languages: [] })
    expect(result.error?.issues[0]?.message).toBe('form_languages')
  })

  it('refuse an unknown currency or time zone', () => {
    expect(localisationSchema.safeParse({ ...localisation, currency: 'XYZ' }).success).toBe(false)
    expect(localisationSchema.safeParse({ ...localisation, timezone: 'Nowhere/Town' }).success).toBe(false)
  })
})

import { describe, expect, it } from 'vitest'
import { appearanceSchema, brandingSchema, companySchema, emailsSchema, formDefaultsSchema, isTimeZone, localisationSchema, notificationsSchema, privacySchema, securitySchema, signinSchema } from '../../shared/utils/settings/schemas'
import { APPEARANCE_PRESETS, FORMALIE_APPEARANCE } from '../../shared/types/appearance'

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

describe('sign-in settings', () => {
  const signin = { methods: ['google', 'password'], code: { sms: true, expiry_minutes: 10, max_attempts: 5 }, allowed_domains: [' @Example.com ', 'example.com', 'Branch.Example.co.uk'] }

  it('keep the sign-in page order and tidy the domains', () => {
    const result = signinSchema.parse(signin)
    expect(result.methods).toEqual(['password', 'google'])
    expect(result.allowed_domains).toEqual(['example.com', 'branch.example.co.uk'])
  })

  it('need one way to sign in, known code rules and real domains', () => {
    const result = signinSchema.safeParse({ ...signin, methods: [], code: { ...signin.code, expiry_minutes: 7 }, allowed_domains: ['not a domain'] })
    expect(result.success).toBe(false)
    const fields = (result.error?.issues ?? []).map(issue => issue.path.join('.'))
    expect(fields).toEqual(expect.arrayContaining(['methods', 'code.expiry_minutes', 'allowed_domains.0']))
  })
})

describe('security settings', () => {
  const security = {
    password: { min_length: 12, lower: true, upper: true, number: true, symbol: false, reuse_last: 5, expiry_days: 0 },
    sessions: { idle_minutes: 60, max_hours: 168 },
    ip_allowlist: { enabled: true, entries: [{ value: '203.0.113.0/24', label: 'Head office' }, { value: ' ', label: null }, { value: '2001:db8::/32', label: '' }] },
  }

  it('drop blank address rows and accept IPv4 and IPv6 ranges', () => {
    const result = securitySchema.parse(security)
    expect(result.ip_allowlist.entries).toEqual([
      { value: '203.0.113.0/24', label: 'Head office' },
      { value: '2001:db8::/32', label: null },
    ])
  })

  it('refuse bad addresses, an empty list that is on, and unknown session lengths', () => {
    expect(securitySchema.safeParse({ ...security, ip_allowlist: { enabled: true, entries: [] } }).error?.issues[0]?.message).toBe('ip_empty')
    expect(securitySchema.safeParse({ ...security, ip_allowlist: { enabled: false, entries: [{ value: '300.1.1.1', label: null }] } }).success).toBe(false)
    expect(securitySchema.safeParse({ ...security, sessions: { idle_minutes: 61, max_hours: 168 } }).success).toBe(false)
    expect(securitySchema.safeParse({ ...security, password: { ...security.password, min_length: 6 } }).success).toBe(false)
  })
})

describe('notification settings', () => {
  const rule = { in_app: true, email: false, to: 'admins', people: [] }
  const events = Object.fromEntries(['response_new', 'response_duplicate', 'form_limit', 'form_closing', 'export_ready', 'webhook_failing', 'security_alert'].map(key => [key, rule]))

  it('take a rule for every event and a summary hour', () => {
    expect(notificationsSchema.safeParse({ events, digest: { enabled: true, hour: 8 } }).success).toBe(true)
  })

  it('need people when the rule says chosen people, and a real hour', () => {
    const result = notificationsSchema.safeParse({ events: { ...events, form_limit: { ...rule, to: 'people', people: [] } }, digest: { enabled: true, hour: 24 } })
    const fields = (result.error?.issues ?? []).map(issue => issue.path.join('.'))
    expect(fields).toEqual(expect.arrayContaining(['events.form_limit.people', 'digest.hour']))
  })
})

describe('email settings', () => {
  it('keep own texts per template and language, empty sender values as null', () => {
    const result = emailsSchema.parse({ sender_name: ' ', reply_to: '', footer: null, custom: { invitation: { de: { subject: 'Einladung', body: 'Hallo {{name}}' } } } })
    expect(result.sender_name).toBeNull()
    expect(result.reply_to).toBeNull()
    expect(result.custom.invitation?.de?.subject).toBe('Einladung')
  })

  it('refuse an empty subject, an unknown template and a bad reply-to', () => {
    expect(emailsSchema.safeParse({ sender_name: null, reply_to: null, footer: null, custom: { invitation: { en: { subject: '', body: 'x' } } } }).success).toBe(false)
    expect(emailsSchema.safeParse({ sender_name: null, reply_to: null, footer: null, custom: { unknown: { en: { subject: 'a', body: 'b' } } } }).success).toBe(false)
    expect(emailsSchema.safeParse({ sender_name: null, reply_to: 'nobody', footer: null, custom: {} }).success).toBe(false)
  })
})

describe('privacy settings', () => {
  it('take a known period, an https notice and empty texts as null', () => {
    const result = privacySchema.parse({ retention_days: 365, notice_url: 'https://www.example.com/privacy', consent: true, consent_text: ' ' })
    expect(result.consent_text).toBeNull()
  })

  it('refuse other periods and plain http', () => {
    expect(privacySchema.safeParse({ retention_days: 45, notice_url: null, consent: false, consent_text: null }).success).toBe(false)
    expect(privacySchema.safeParse({ retention_days: 0, notice_url: 'http://example.com/privacy', consent: false, consent_text: null }).error?.issues[0]?.message).toBe('https')
  })
})

describe('form defaults', () => {
  const defaults = { settings: { progress_bar: true, save_resume: false, field_icons: true, label_position: 'top' }, theme_id: null, thank_you: { title: '', message: null }, team_emails: [], embed_domains: ['https://www.Example.com/forms', '*.example.org'] }

  it('tidy embed websites to host names', () => {
    const result = formDefaultsSchema.parse(defaults)
    expect(result.embed_domains).toEqual(['www.example.com', '*.example.org'])
    expect(result.thank_you.title).toBeNull()
  })

  it('refuse a website that is not a host name', () => {
    expect(formDefaultsSchema.safeParse({ ...defaults, embed_domains: ['not a site'] }).success).toBe(false)
  })
})

describe('appearance', () => {
  it('take Formalie’s look and every preset', () => {
    expect(appearanceSchema.safeParse(FORMALIE_APPEARANCE).success).toBe(true)
    for (const [key, preset] of Object.entries(APPEARANCE_PRESETS)) expect(appearanceSchema.safeParse({ ...FORMALIE_APPEARANCE, ...preset, preset: key }).success).toBe(true)
  })

  it('refuse colours and sizes outside the safe set', () => {
    expect(appearanceSchema.safeParse({ ...FORMALIE_APPEARANCE, primary: '#ff0000' }).success).toBe(false)
    expect(appearanceSchema.safeParse({ ...FORMALIE_APPEARANCE, font: 'comic' }).success).toBe(false)
  })
})

"""Records the frontend's settings rules into tests/vectors/settings_rules.json (B3):

- the catalogues the settings use (industries, sizes, formats, appearance choices, email templates, notification
  events, retention, countries and currencies, session choices, settings sections, the Formalie appearance);
- every settings schema (shared/utils/settings/schemas.ts) run over many inputs: accepted or not, the cleaned value,
  and each problem's field and message;
- IP and range parsing (shared/utils/apiService/access.ts), time zones, and `settingsChanges` (the audit lines).

    fmly\\Scripts\\python.exe scripts\\dump_settings_rules.py [path\\to\\formalieFrontend]

The frontend is only read. Then scripts/gen_frontend_catalogues.py writes app/modules/settings/catalogues.py, and
tests/parity/test_settings_rules.py holds the Pydantic schemas to these answers.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from dump_frontend_rules import ROOT, run_in_node  # noqa: E402

OUT = ROOT / "tests" / "vectors" / "settings_rules.json"

ENTRY = r"""
import * as S from '__SHARED__/utils/settings/schemas.ts'
import * as O from '__SHARED__/types/onboarding.ts'
import * as A from '__SHARED__/types/appearance.ts'
import { EMAIL_TEMPLATES } from '__SHARED__/types/emails.ts'
import { NOTIFICATION_EVENTS } from '__SHARED__/types/notifications.ts'
import { RETENTION_DAYS } from '__SHARED__/types/privacy.ts'
import { SETTINGS_SECTIONS } from '__SHARED__/types/settings.ts'
import { COUNTRY_CURRENCIES, CURRENCY_CODES } from '__SHARED__/utils/platform/countries.ts'
import { isTimeZone } from '__SHARED__/utils/forms/catalogues.ts'
import { parseCidr, ipInCidr } from '__SHARED__/utils/apiService/access.ts'
import { STARTER_TEMPLATE_KEYS } from '__SHARED__/utils/templates/starters.ts'
import { ONBOARDING_STEPS } from '__SHARED__/types/onboarding.ts'
import { z } from '__SHARED__/../node_modules/zod'
import { APP_LOCALES } from '__SHARED__/utils/i18n/locales.ts'
import { SYSTEM_TEMPLATES, TEMPLATE_CATEGORIES, TEMPLATE_CATEGORY_KEYS } from '__SHARED__/templates/index.ts'
import { THEME_PRESETS } from '__SHARED__/utils/forms/theme.ts'
import { PAGE_PRESETS } from '__SHARED__/utils/forms/page-design.ts'
import { DATASOURCE_STATUSES } from '__SHARED__/types/datasources.ts'
import { ORG_KINDS } from '__SHARED__/types/org.ts'

const clone = v => JSON.parse(JSON.stringify(v))
const set = (base, path, value) => {
  const out = clone(base)
  const keys = path.split('.')
  let at = out
  for (const k of keys.slice(0, -1)) at = at[k]
  if (value === '__DELETE__') delete at[keys.at(-1)]
  else at[keys.at(-1)] = value
  return out
}
const run = (schema, input) => {
  const r = schema.safeParse(input)
  return r.success ? { input, ok: true, data: r.data } : { input, ok: false, issues: r.error.issues.map(i => ({ path: i.path.join('.'), message: i.message })) }
}
const variants = (base, list) => [base, ...list.map(([p, v]) => set(base, p, v)), 'nonsense', null, 42, []]

const company = { legal_name: 'Remedy Legal Ltd', display_name: 'Remedy Legal', industry: null, size: null, website: null,
  registration_number: null, tax_number: null, support_email: null, support_phone: null,
  address: { line1: null, line2: null, city: null, region: null, postal_code: null, country: null } }
const companyCases = variants(company, [
  ['legal_name', '  R  '], ['legal_name', 'x'.repeat(161)], ['display_name', '  Remedy  '], ['display_name', 'R'], ['legal_name', 5],
  ['industry', O.INDUSTRIES[0]], ['industry', 'space'], ['size', '11-50'], ['size', '12'],
  ['website', 'https://remedy.example'], ['website', 'remedy.example'], ['website', ''], ['website', '  https://a.b/c  '], ['website', 'http://localhost'],
  ['registration_number', '  '], ['tax_number', 'GB123'], ['support_email', 'help@remedy.example'], ['support_email', 'nope'], ['support_email', ''],
  ['support_phone', '+44 7700 900123'], ['support_phone', 'call me'], ['support_phone', '12345'],
  ['address.country', 'GB'], ['address.country', 'gb'], ['address.country', 'XX'], ['address.country', ''], ['address.city', '  London '],
  ['address', '__DELETE__'], ['address.postal_code', 'x'.repeat(21)], ['extra_field', 'ignored'],
])

const brandingCases = variants({ brand_color: null, signin_message: null }, [
  ['brand_color', '#1a2B3c'], ['brand_color', '#123'], ['brand_color', 'red'], ['signin_message', '  Welcome  '], ['signin_message', 'x'.repeat(161)],
  ['logo_upload_id', null], ['logo_upload_id', 'abc'], ['logo_upload_id', ''], ['favicon_upload_id', 'x'.repeat(101)], ['logo_dark_upload_id', 7],
  ['brand_color', '__DELETE__'],
])

const localisation = { language: 'en', timezone: 'UTC', currency: 'USD', date_format: 'DD/MM/YYYY', number_format: '1,234.56', week_start: 'monday', form_languages: ['en', 'fr'] }
const localisationCases = variants(localisation, [
  ['language', 'fr'], ['language', 'xx'], ['timezone', 'Europe/London'], ['timezone', 'europe/london'], ['timezone', 'Mars/Base'], ['timezone', ''],
  ['timezone', 'America/Argentina/Buenos_Aires'], ['timezone', 'Asia/Calcutta'], ['timezone', 'GMT'], ['timezone', 'Etc/GMT+5'],
  ['currency', 'GBP'], ['currency', 'XYZ'], ['currency', 'gbp'], ['date_format', 'YYYY-MM-DD'], ['date_format', 'D/M/Y'],
  ['number_format', "1'234.56"], ['number_format', '1234'], ['week_start', 'sunday'], ['week_start', 'friday'],
  ['form_languages', []], ['form_languages', ['en', 'xx']], ['form_languages', ['en', 'en']],
])

const signin = { methods: ['password'], code: { sms: false, expiry_minutes: 5, max_attempts: 5 }, allowed_domains: [] }
const signinCases = variants(signin, [
  ['methods', []], ['methods', ['google', 'password']], ['methods', ['facebook', 'facebook', 'microsoft']], ['methods', ['apple']],
  ['code.expiry_minutes', 10], ['code.expiry_minutes', 7], ['code.max_attempts', 3], ['code.max_attempts', 4], ['code.sms', 'yes'],
  ['allowed_domains', ['Example.COM', '@example.com', ' sub.example.co.uk ']], ['allowed_domains', ['localhost']], ['allowed_domains', ['a@b.com']],
  ['allowed_domains', Array.from({ length: 51 }, (_, i) => `d${i}.example`)],
])

const security = { password: { min_length: 10, lower: true, upper: true, number: true, symbol: false, reuse_last: 0, expiry_days: 0 },
  sessions: { idle_minutes: 60, max_hours: 168 }, ip_allowlist: { enabled: false, entries: [] } }
const securityCases = variants(security, [
  ['password.min_length', 7], ['password.min_length', 8], ['password.min_length', 64], ['password.min_length', 65], ['password.min_length', 10.5],
  ['password.reuse_last', 3], ['password.reuse_last', 4], ['password.expiry_days', 90], ['password.expiry_days', 30],
  ['sessions.idle_minutes', 15], ['sessions.idle_minutes', 45], ['sessions.max_hours', 8], ['sessions.max_hours', 9],
  ['ip_allowlist.enabled', true],
  ['ip_allowlist', { enabled: true, entries: [{ value: '203.0.113.0/24', label: '  Office ' }, { value: '  ', label: null }, { value: '2001:db8::/32', label: '' }] }],
  ['ip_allowlist', { enabled: true, entries: [{ value: '300.1.1.1', label: null }] }],
  ['ip_allowlist', { enabled: false, entries: [{ value: '10.0.0.1/33', label: null }] }],
  ['ip_allowlist', { enabled: true, entries: [{ value: '', label: 'x' }] }],
])

const rule = (in_app, email, to = 'admins') => ({ in_app, email, to, people: [] })
const notifications = { events: Object.fromEntries(NOTIFICATION_EVENTS.map(e => [e, rule(true, false)])), digest: { enabled: false, hour: 8 } }
const notificationCases = variants(notifications, [
  ['events.response_new.to', 'everyone'], ['events.response_new.to', 'people'], ['events.response_new', { in_app: true, email: true, to: 'people', people: ['u1'] }],
  ['events.response_new.to', 'nobody'], ['events.form_limit', '__DELETE__'], ['digest.hour', 24], ['digest.hour', 0], ['digest.hour', 7.5], ['events.extra', rule(true, true)],
])

const emails = { sender_name: null, reply_to: null, footer: null, custom: {} }
const emailCases = variants(emails, [
  ['sender_name', '  Remedy  '], ['reply_to', 'hello@remedy.example'], ['reply_to', 'bad'], ['footer', 'x'.repeat(301)],
  ['custom', { signin_code: { en: { subject: ' Your code ', body: 'Code: {{code}}' } } }],
  ['custom', { signin_code: { xx: { subject: 'a', body: 'b' } } }], ['custom', { unknown: { en: { subject: 'a', body: 'b' } } }],
  ['custom', { invitation: { fr: { subject: '', body: 'b' } } }], ['custom', { invitation: { fr: { subject: 'a', body: 'x'.repeat(10001) } } }],
])

const privacy = { retention_days: 0, notice_url: null, consent: false, consent_text: null }
const privacyCases = variants(privacy, [
  ['retention_days', 30], ['retention_days', 31], ['notice_url', 'https://remedy.example/privacy'], ['notice_url', 'http://remedy.example/privacy'],
  ['notice_url', ''], ['consent', true], ['consent_text', '  I agree  '], ['consent_text', 'x'.repeat(401)],
])

const formDefaults = { settings: { progress_bar: true, save_resume: false, field_icons: true, label_position: 'top' }, theme_id: null,
  thank_you: { title: null, message: null }, team_emails: [], embed_domains: [] }
const formDefaultCases = variants(formDefaults, [
  ['settings.label_position', 'left'], ['settings.label_position', 'right'], ['theme_id', 'abc'], ['thank_you.title', '  Thanks!  '],
  ['team_emails', ['u1', 'u2']], ['embed_domains', ['https://Shop.Example.com/page', '*.example.org', 'example.org', 'example.org']],
  ['embed_domains', ['not a domain']], ['embed_domains', ['**.example.com']],
])

const appearanceCases = variants(clone(A.FORMALIE_APPEARANCE), [
  ['primary', 'blue'], ['primary', 'chartreuse'], ['neutral', 'slate'], ['radius', 'xl'], ['font', 'serif'], ['text_size', 'xl'],
  ['dark', { primary: 'mono', neutral: 'zinc', background: 'plain' }], ['dark', { primary: 'mono', neutral: 'zinc' }], ['default_mode', 'auto'],
  ['header.search', 'no'], ['preset', 'x'.repeat(41)],
])

// Onboarding (server/mock/routes/onboarding.ts: the schemas live in the mock route, copied here as they are)
const ob = {
  company: z.object({ name: z.string().trim().min(2).max(120), industry: z.enum(O.INDUSTRIES).nullable(), size: z.enum(O.COMPANY_SIZES).nullable(),
    country: z.string().refine(v => v in COUNTRY_CURRENCIES, 'Choose a country.').nullable(), website: z.url().max(200).nullable() }),
  branding: z.object({ logo_upload_id: z.string().nullable(), brand_color: z.string().regex(/^#[0-9a-fA-F]{6}$/).nullable() }),
  localisation: z.object({ language: z.enum(APP_LOCALES.map(item => item.code)),
    timezone: z.string().min(1).max(64), currency: z.string().refine(code => CURRENCY_CODES.includes(code), 'Choose a currency.'),
    date_format: z.enum(O.DATE_FORMATS), number_format: z.enum(O.NUMBER_FORMATS), week_start: z.enum(['monday', 'sunday', 'saturday']) }),
  team: z.object({ invites: z.array(z.object({ email: z.email(), role: z.enum(['admin', 'member']) })).max(20)
    .refine(list => new Set(list.map(i => i.email.toLowerCase())).size === list.length, 'Each email once.') }),
  first_form: z.object({ choice: z.enum(['blank', 'template']).nullable(), template_key: z.enum(STARTER_TEMPLATE_KEYS).nullable() }),
  patch: z.object({ step: z.enum(ONBOARDING_STEPS), action: z.enum(['save', 'skip']), data: z.unknown().optional() }),
}
const obCompany = { name: 'Acme Labs', industry: null, size: null, country: null, website: null }
const urls = ['https://acme.example', 'http://acme.example/path?q=1', 'acme.example', 'ftp://files.example', 'mailto:hi@acme.example',
  'https://', 'https://localhost', 'https://acme', 'javascript:alert(1)', 'https://exa mple.com', ' https://acme.example ', 'https://acme.example:99999',
  'HTTPS://ACME.EXAMPLE', 'https://ünï.example', 'https://acme.example/' + 'x'.repeat(200), 'urn:isbn:123', 'https://[::1]/', 'https://user:pw@acme.example']
const onboardingCases = {
  company: variants(obCompany, [['name', ' A '], ['name', 'x'.repeat(121)], ['country', 'GB'], ['country', 'XX'], ['industry', 'legal'],
    ...urls.map(u => ['website', u])]),
  branding: variants({ logo_upload_id: null, brand_color: null }, [['brand_color', '#ABCDEF'], ['brand_color', 'blue'], ['logo_upload_id', 'abc'], ['logo_upload_id', '__DELETE__']]),
  localisation: variants({ language: 'en', timezone: 'UTC', currency: 'USD', date_format: 'DD/MM/YYYY', number_format: '1,234.56', week_start: 'monday' },
    [['timezone', 'Mars/Base'], ['timezone', ''], ['currency', 'XYZ'], ['language', 'xx']]),
  team: variants({ invites: [] }, [['invites', [{ email: 'a@b.example', role: 'admin' }, { email: 'A@B.example', role: 'member' }]],
    ['invites', [{ email: 'nope', role: 'member' }]], ['invites', [{ email: 'a@b.example', role: 'owner' }]],
    ['invites', Array.from({ length: 21 }, (_, i) => ({ email: `p${i}@b.example`, role: 'member' }))],
    ['invites', [{ email: 'ada@lovelace.test', role: 'member' }, { email: 'grace@hopper.test', role: 'admin' }]]]),
  first_form: variants({ choice: null, template_key: null }, [['choice', 'template'], ['template_key', STARTER_TEMPLATE_KEYS[0]], ['template_key', 'nope'], ['choice', 'copy']]),
  patch: variants({ step: 'company', action: 'save', data: {} }, [['step', 'billing'], ['action', 'later'], ['data', '__DELETE__'], ['data', null]]),
}

const settingsChanges = (before, after, prefix = '') => Object.keys(after).flatMap(key => {
  const a = before[key]; const b = after[key]
  if (b && typeof b === 'object' && !Array.isArray(b)) return settingsChanges(a ?? {}, b, `${prefix}${key}.`)
  const show = v => (v == null || v === '' ? null : Array.isArray(v) ? v.join(', ') : String(v))
  return show(a) === show(b) ? [] : [{ field: `${prefix}${key}`, before: show(a), after: show(b) }]
})
const changeCases = [
  [company, set(company, 'display_name', 'Remedy')],
  [company, set(set(company, 'address.city', 'London'), 'website', 'https://a.example')],
  [signin, set(signin, 'methods', ['password', 'google'])],
  [security, set(set(security, 'sessions.idle_minutes', 30), 'password.symbol', true)],
  [{ a: 1, b: '' }, { a: 1.0, b: null, c: false }],
].map(([b, a]) => ({ before: b, after: a, changes: settingsChanges(b, a) }))

const ips = ['203.0.113.7', '203.0.113.0/24', '10.0.0.1/33', '300.1.1.1', '::1', '2001:db8::/32', '2001:db8::1/129', '::ffff:10.0.0.1',
  '1:2:3:4:5:6:7:8', '1::2::3', 'fe80::1%eth0', 'abc', '', ' 10.0.0.0/8 ', '10.0.0.0/08', '10.0.0.0/', '1.2.3.4/32/5']
const ipMatches = [['203.0.113.7', '203.0.113.0/24'], ['203.0.114.7', '203.0.113.0/24'], ['::ffff:203.0.113.7', '203.0.113.0/24'],
  ['2001:db8::5', '2001:db8::/32'], ['10.1.2.3', '0.0.0.0/0'], ['10.1.2.3', '::/0'], ['127.0.0.1', '127.0.0.1']]
const zones = ['UTC', 'Europe/London', 'europe/london', 'Asia/Calcutta', 'Asia/Kolkata', 'US/Eastern', 'GMT', 'Etc/GMT+5', 'Mars/Base', '', 'EST', 'America/Argentina/Buenos_Aires', 'Africa/Lagos']

process.stdout.write(JSON.stringify({
  industries: O.INDUSTRIES, company_sizes: O.COMPANY_SIZES, date_formats: O.DATE_FORMATS, number_formats: O.NUMBER_FORMATS,
  appearance_primaries: A.APPEARANCE_PRIMARIES, appearance_neutrals: A.APPEARANCE_NEUTRALS, appearance_radii: A.APPEARANCE_RADII,
  appearance_fonts: A.APPEARANCE_FONTS, formalie_appearance: A.FORMALIE_APPEARANCE, email_templates: EMAIL_TEMPLATES,
  notification_events: NOTIFICATION_EVENTS, retention_days: RETENTION_DAYS, settings_sections: SETTINGS_SECTIONS,
  country_currencies: COUNTRY_CURRENCIES, currency_codes: CURRENCY_CODES, idle_minutes: S.IDLE_MINUTES,
  max_session_hours: S.MAX_SESSION_HOURS, signin_methods: S.SIGNIN_METHODS,
  schemas: {
    company: companyCases.map(i => run(S.companySchema, i)),
    branding: brandingCases.map(i => run(S.brandingSchema, i)),
    localisation: localisationCases.map(i => run(S.localisationSchema, i)),
    signin: signinCases.map(i => run(S.signinSchema, i)),
    security: securityCases.map(i => run(S.securitySchema, i)),
    notifications: notificationCases.map(i => run(S.notificationsSchema, i)),
    emails: emailCases.map(i => run(S.emailsSchema, i)),
    privacy: privacyCases.map(i => run(S.privacySchema, i)),
    form_defaults: formDefaultCases.map(i => run(S.formDefaultsSchema, i)),
    appearance: appearanceCases.map(i => run(S.appearanceSchema, i)),
  },
  // Navigation counts (server/mock/routes/navigation.ts): the system lists' sizes
  system_templates: SYSTEM_TEMPLATES.map(t => ({ key: t.key, category: t.category })), template_category_keys: TEMPLATE_CATEGORY_KEYS,
  system_theme_count: THEME_PRESETS.length - 1 + TEMPLATE_CATEGORIES.length, system_page_count: PAGE_PRESETS.length,
  datasource_statuses: DATASOURCE_STATUSES, org_kinds: ORG_KINDS,
  starter_template_keys: STARTER_TEMPLATE_KEYS, onboarding_steps: ONBOARDING_STEPS,
  onboarding: Object.fromEntries(Object.entries(onboardingCases).map(([k, cases]) => [k, cases.map(i => run(ob[k], i))])),
  settings_changes: changeCases,
  ip_ranges: ips.map(v => ({ value: v, valid: !!parseCidr(v) })),
  ip_matches: ipMatches.map(([ip, cidr]) => ({ ip, cidr, match: ipInCidr(ip, cidr) })),
  time_zones: zones.map(z => ({ value: z, valid: isTimeZone(z) })),
}))
"""


def main() -> None:
    data = run_in_node(ENTRY)
    data["about"] = "Recorded from the frontend's shared/ code by scripts/dump_settings_rules.py. Do not edit."
    OUT.write_text(json.dumps(data, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    cases = sum(len(v) for v in data["schemas"].values())
    print(f"Wrote {OUT.relative_to(ROOT)}: {cases} schema cases, {len(data['ip_ranges'])} ranges, "
          f"{len(data['time_zones'])} time zones")


if __name__ == "__main__":
    main()

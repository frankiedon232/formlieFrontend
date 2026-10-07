/**
 * Validation for workspace settings (F14), shared by the Settings pages (field errors as people type)
 * and the API (the same rules on save). Empty optional texts become null.
 */
import { z } from 'zod'
import { COMPANY_SIZES, DATE_FORMATS, INDUSTRIES, NUMBER_FORMATS } from '../../types/onboarding'
import { EMAIL_TEMPLATES, type EmailTemplateKey } from '../../types/emails'
import { NOTIFICATION_EVENTS, type NotificationEvent } from '../../types/notifications'
import { parseCidr } from '../apiService/access'
import { PASSWORD_LENGTH_RANGE } from '../auth/password'
import { APP_LOCALES } from '../i18n/locales'
import { CURRENCY_CODES, isCountryCode } from '../platform/countries'

/** Optional text: trimmed, '' → null, at most `max` characters. */
const optional = (max: number) =>
  z
    .string()
    .trim()
    .max(max)
    .nullable()
    .transform(value => value || null)

const LOCALE_CODES = APP_LOCALES.map(item => item.code) as [string, ...string[]]

/** A real IANA time zone (whatever this runtime knows), or UTC. */
export function isTimeZone(value: string): boolean {
  if (value === 'UTC') return true
  try {
    new Intl.DateTimeFormat('en', { timeZone: value })
    return true
  } catch {
    return false
  }
}

export const companySchema = z.object({
  legal_name: z.string().trim().min(2).max(160),
  display_name: z.string().trim().min(2).max(80),
  industry: z.enum(INDUSTRIES).nullable(),
  size: z.enum(COMPANY_SIZES).nullable(),
  website: optional(200).refine(value => !value || /^https?:\/\/[^\s.]+\.[^\s]+$/i.test(value), 'website'),
  registration_number: optional(60),
  tax_number: optional(60),
  support_email: optional(200).refine(value => !value || z.email().safeParse(value).success, 'email'),
  support_phone: optional(40).refine(value => !value || /^\+?[0-9 ()./-]{6,40}$/.test(value), 'phone'),
  address: z.object({
    line1: optional(160),
    line2: optional(160),
    city: optional(100),
    region: optional(100),
    postal_code: optional(20),
    country: z
      .string()
      .nullable()
      .refine(value => !value || isCountryCode(value), 'country'),
  }),
})

const uploadId = z.string().min(1).max(100).nullable().optional()
export const brandingSchema = z.object({
  logo_upload_id: uploadId,
  logo_dark_upload_id: uploadId,
  favicon_upload_id: uploadId,
  signin_image_upload_id: uploadId,
  brand_color: z
    .string()
    .regex(/^#[0-9a-fA-F]{6}$/, 'color')
    .nullable(),
  signin_message: optional(160),
})

export const localisationSchema = z.object({
  language: z.enum(LOCALE_CODES),
  timezone: z.string().min(1).max(64).refine(isTimeZone, 'timezone'),
  currency: z.string().refine(code => CURRENCY_CODES.includes(code), 'currency'),
  date_format: z.enum(DATE_FORMATS),
  number_format: z.enum(NUMBER_FORMATS),
  week_start: z.enum(['monday', 'sunday', 'saturday']),
  form_languages: z.array(z.enum(LOCALE_CODES)).min(1, 'form_languages').max(LOCALE_CODES.length),
})

/** Sign-in methods, in the order the sign-in page shows them. */
export const SIGNIN_METHODS = ['password', 'google', 'microsoft', 'apple', 'facebook'] as const
/** example.com, sub.example.co.uk (no scheme, no @). */
export const isEmailDomain = (value: string) => /^(?=.{3,253}$)([a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,63}$/.test(value)
/** An IPv4 / IPv6 address or CIDR range. */
export const isIpOrRange = (value: string) => !!parseCidr(value)
export const IDLE_MINUTES = [15, 30, 60, 120, 240, 480, 720] as const
/** The owner's minimum (2026-10-02); shorter asks for confirmation in Settings. */
export const IDLE_MINUTES_SAFE = 60
export const MAX_SESSION_HOURS = [8, 12, 24, 72, 168] as const

export const signinSchema = z.object({
  methods: z
    .array(z.enum(SIGNIN_METHODS))
    .min(1, 'methods')
    .transform(list => SIGNIN_METHODS.filter(method => list.includes(method))),
  code: z.object({
    sms: z.boolean(),
    expiry_minutes: z.union([z.literal(5), z.literal(10), z.literal(15)]),
    max_attempts: z.union([z.literal(3), z.literal(5), z.literal(10)]),
  }),
  allowed_domains: z
    .array(
      z
        .string()
        .trim()
        .toLowerCase()
        .transform(value => value.replace(/^@/, ''))
        .refine(isEmailDomain, 'domain'),
    )
    .max(50)
    .transform(list => [...new Set(list)]),
})

export const securitySchema = z.object({
  password: z.object({
    min_length: z.number().int().min(PASSWORD_LENGTH_RANGE.min).max(PASSWORD_LENGTH_RANGE.max),
    lower: z.boolean(),
    upper: z.boolean(),
    number: z.boolean(),
    symbol: z.boolean(),
    reuse_last: z.union([z.literal(0), z.literal(3), z.literal(5), z.literal(10)]),
    expiry_days: z.union([z.literal(0), z.literal(90), z.literal(180), z.literal(365)]),
  }),
  sessions: z.object({
    idle_minutes: z.number().refine(value => (IDLE_MINUTES as readonly number[]).includes(value)),
    max_hours: z.number().refine(value => (MAX_SESSION_HOURS as readonly number[]).includes(value)),
  }),
  ip_allowlist: z.object({
    enabled: z.boolean(),
    // Empty rows (an added line left blank) are dropped
    entries: z.preprocess(
      list => (Array.isArray(list) ? list.filter(entry => String((entry as { value?: unknown } | null)?.value ?? '').trim()) : list),
      z.array(
        z.object({
          value: z.string().trim().refine(isIpOrRange, 'ip'),
          label: optional(60),
        }),
      ).max(100),
    ),
  }).refine(list => !list.enabled || list.entries.length > 0, { message: 'ip_empty', path: ['entries'] }),
})

const notificationRule = z.object({
  in_app: z.boolean(),
  email: z.boolean(),
  to: z.enum(['admins', 'everyone', 'people']),
  people: z.array(z.string().max(64)).max(200),
}).refine(rule => rule.to !== 'people' || rule.people.length > 0, { message: 'people', path: ['people'] })

export const notificationsSchema = z.object({
  events: z.object(Object.fromEntries(NOTIFICATION_EVENTS.map(key => [key, notificationRule])) as Record<NotificationEvent, typeof notificationRule>),
  digest: z.object({ enabled: z.boolean(), hour: z.number().int().min(0).max(23) }),
})

export const emailTextSchema = z.object({ subject: z.string().trim().min(1, 'subject').max(200), body: z.string().trim().min(1, 'body').max(10_000) })

export const emailsSchema = z.object({
  sender_name: optional(80),
  reply_to: optional(200).refine(value => !value || z.email().safeParse(value).success, 'email'),
  footer: optional(300),
  custom: z.partialRecord(z.enum(EMAIL_TEMPLATES), z.partialRecord(z.enum(LOCALE_CODES), emailTextSchema)) as unknown as z.ZodType<Partial<Record<EmailTemplateKey, Record<string, z.infer<typeof emailTextSchema>>>>>,
})

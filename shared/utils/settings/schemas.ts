/**
 * Validation for workspace settings (F14), shared by the Settings pages (field errors as people type)
 * and the API (the same rules on save). Empty optional texts become null.
 */
import { z } from 'zod'
import { COMPANY_SIZES, DATE_FORMATS, INDUSTRIES, NUMBER_FORMATS } from '../../types/onboarding'
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

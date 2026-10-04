/**
 * Answer validation, one set of rules for the form renderer and the API (the server re-checks
 * every submission with the same function). Returns the first problem with an answer, or null.
 *
 *   required · email · url · phone · number + min / max · text length · pattern · choices count ·
 *   file count · date range order · address parts (street, city, country, postal code unless
 *   switched off, region when switched on, also when an optional address is only partly filled).
 */
import type { FormField } from './build'
import { isCurrencyCode, isLanguageCode, isTimeZone } from './catalogues'

export type AnswerProblem =
  | 'required' | 'email' | 'url' | 'phone' | 'number' | 'min' | 'max'
  | 'min_length' | 'max_length' | 'pattern' | 'min_selected' | 'max_selected'
  | 'max_files' | 'file' | 'date_range' | 'address'
  | 'ip' | 'domain' | 'mac' | 'iban' | 'bic' | 'color' | 'duration' | 'name' | 'consent' | 'choice'

export interface ValidationIssue {
  code: AnswerProblem
  params?: Record<string, string | number>
  /** Address: which parts are missing (keys of the address value). */
  parts?: AddressPart[]
}

export type AddressPart = 'line1' | 'city' | 'region' | 'postal_code' | 'country'

const EMAIL = /^[^\s@]+@[^\s@.]+(\.[^\s@.]+)*\.[^\s@.]{2,}$/
const NUMERIC_TYPES = ['number', 'currency', 'slider', 'scale', 'rating', 'percentage']
const TEXT_TYPES = ['short_text', 'long_text', 'email', 'url', 'phone']

const IPV4 = /^(25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)(\.(25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)){3}$/
/** IPv6 incl. "::" shortening and an IPv4 tail. */
export function isIpv6(value: string): boolean {
  if (!/^[0-9a-f:.]+$/i.test(value) || (value.match(/::/g)?.length ?? 0) > 1) return false
  let parts = value.split(':')
  let groups = 8
  const tail = parts.at(-1) ?? ''
  if (tail.includes('.')) {
    if (!IPV4.test(tail)) return false
    parts = parts.slice(0, -1)
    groups = 6
  }
  const filled = parts.filter(Boolean)
  if (!filled.every(group => /^[0-9a-f]{1,4}$/i.test(group))) return false
  return value.includes('::') ? filled.length < groups : filled.length === groups && parts.length === groups
}
export const isIpv4 = (value: string) => IPV4.test(value)
const DOMAIN = /^(?=.{1,253}$)(?!-)([a-z0-9-]{1,63}(?<!-)\.)+[a-z]{2,63}$/i
const MAC = /^([0-9a-f]{2}[:-]){5}[0-9a-f]{2}$|^([0-9a-f]{4}\.){2}[0-9a-f]{4}$/i
const BIC = /^[A-Z]{4}[A-Z]{2}[A-Z0-9]{2}([A-Z0-9]{3})?$/
/** IBAN: country, check digits, then the ISO 7064 mod-97 checksum. */
export function isIban(value: string): boolean {
  const iban = value.replace(/\s+/g, '').toUpperCase()
  if (!/^[A-Z]{2}\d{2}[A-Z0-9]{10,30}$/.test(iban)) return false
  const moved = iban.slice(4) + iban.slice(0, 4)
  let rest = 0
  for (const char of moved) {
    const code = /[A-Z]/.test(char) ? String(char.charCodeAt(0) - 55) : char
    for (const digit of code) rest = (rest * 10 + Number(digit)) % 97
  }
  return rest === 1
}

export const isBlank = (value: unknown): boolean =>
  value == null ||
  value === '' ||
  value === false ||
  (Array.isArray(value) && !value.length) ||
  (typeof value === 'object' && !Array.isArray(value) && !(value instanceof Blob) &&
    !Object.values(value as object).some(v => v != null && String(v).trim() !== ''))

/** Visible text of rich text HTML (what length limits count). */
export const plainText = (html: string) =>
  html.replace(/<[^>]*>/g, '').replace(/&nbsp;/g, ' ').replace(/&[a-z]+;|&#\d+;/gi, 'x')

/** The address parts a field asks for (postal code on by default, region off). */
export function requiredAddressParts(field: FormField): AddressPart[] {
  const p = field.props ?? {}
  return [
    'line1', 'city',
    ...(p.require_region === true ? (['region'] as const) : []),
    ...(p.require_postal_code === false ? [] : (['postal_code'] as const)),
    'country',
  ]
}

const num = (value: unknown) => (value === '' || value == null ? NaN : Number(value))

export function validateAnswer(field: FormField, value: unknown, required: boolean): ValidationIssue | null {
  const rules = (field.validation ?? {}) as Record<string, unknown>

  // Address: every required part, as soon as it's required or partly filled in.
  if (field.type === 'address') {
    const address = (value && typeof value === 'object' ? value : {}) as Record<string, unknown>
    const filled = !isBlank(address)
    if (!filled) return required ? { code: 'required' } : null
    const parts = requiredAddressParts(field).filter(part => isBlank(address[part]))
    return parts.length ? { code: 'address', parts } : null
  }

  if (field.type === 'full_name') {
    const name = (value && typeof value === 'object' ? value : {}) as Record<string, unknown>
    if (isBlank(name)) return required ? { code: 'required' } : null
    return isBlank(name.first) || isBlank(name.last) ? { code: 'name' } : null
  }
  if (field.type === 'consent') return required && value !== true ? { code: 'consent' } : null
  if (field.type === 'duration') {
    const d = (value && typeof value === 'object' ? value : {}) as { hours?: unknown; minutes?: unknown }
    if (isBlank(d)) return required ? { code: 'required' } : null
    const h = num(d.hours ?? 0)
    const m = num(d.minutes ?? 0)
    return Number.isNaN(h) || Number.isNaN(m) || h < 0 || m < 0 || m > 59 || h + m === 0 ? { code: 'duration' } : null
  }

  if (field.type === 'date_range') {
    const range = (value && typeof value === 'object' ? value : {}) as { from?: string; to?: string }
    if (!range.from && !range.to) return required ? { code: 'required' } : null
    if (!range.from || !range.to) return { code: 'date_range' }
    return range.from > range.to ? { code: 'date_range' } : null
  }

  const empty = field.type === 'rich_text' ? !plainText(String(value ?? '')).trim() : isBlank(value)
  if (empty) return required ? { code: 'required' } : null

  const text = typeof value === 'string' ? value.trim() : ''
  if (field.type === 'email' && !EMAIL.test(text)) return { code: 'email' }
  if (field.type === 'url') {
    try {
      const url = new URL(text)
      if (!['http:', 'https:'].includes(url.protocol) || !url.hostname.includes('.')) return { code: 'url' }
    } catch {
      return { code: 'url' }
    }
  }
  if (field.type === 'phone') {
    const digits = text.replace(/[\s().-]/g, '')
    if (!/^\+?\d{6,15}$/.test(digits)) return { code: 'phone' }
  }

  if (field.type === 'ip_address') {
    const version = String(field.props?.ip_version ?? 'any')
    const ok = (version !== 'v6' && isIpv4(text)) || (version !== 'v4' && isIpv6(text))
    if (!ok) return { code: 'ip', params: { version } }
  }
  if (field.type === 'domain' && !DOMAIN.test(text.replace(/\.$/, ''))) return { code: 'domain' }
  if (field.type === 'mac_address' && !MAC.test(text)) return { code: 'mac' }
  if (field.type === 'iban' && !isIban(text)) return { code: 'iban' }
  if (field.type === 'bic' && !BIC.test(text.replace(/\s+/g, '').toUpperCase())) return { code: 'bic' }
  if (field.type === 'color' && !/^#[0-9a-f]{6}$/i.test(text)) return { code: 'color' }
  if (field.type === 'language' && !isLanguageCode(text)) return { code: 'choice' }
  if (field.type === 'timezone' && !isTimeZone(text)) return { code: 'choice' }
  if (field.type === 'currency_code' && !isCurrencyCode(text)) return { code: 'choice' }

  if (NUMERIC_TYPES.includes(field.type)) {
    const n = num(value)
    if (Number.isNaN(n)) return { code: 'number' }
    const min = num(rules.min)
    const max = num(rules.max)
    if (!Number.isNaN(min) && n < min) return { code: 'min', params: { min } }
    if (!Number.isNaN(max) && n > max) return { code: 'max', params: { max } }
  }

  if (TEXT_TYPES.includes(field.type) || field.type === 'rich_text') {
    const length = field.type === 'rich_text' ? plainText(String(value)).length : text.length
    const min = num(rules.min_length)
    const max = num(rules.max_length)
    if (!Number.isNaN(min) && length < min) return { code: 'min_length', params: { n: min } }
    if (!Number.isNaN(max) && length > max) return { code: 'max_length', params: { n: max } }
    if (typeof rules.pattern === 'string' && rules.pattern && field.type !== 'rich_text') {
      try {
        if (!new RegExp(rules.pattern).test(text)) return { code: 'pattern' }
      } catch {
        // An invalid pattern can't be checked (the builder flags it).
      }
    }
  }

  if (Array.isArray(value) && ['checkbox', 'multi_select'].includes(field.type)) {
    const min = num(rules.min_selected)
    const max = num(rules.max_selected)
    if (!Number.isNaN(min) && value.length < min) return { code: 'min_selected', params: { n: min } }
    if (!Number.isNaN(max) && value.length > max) return { code: 'max_selected', params: { n: max } }
  }

  if (['file_upload', 'image_upload'].includes(field.type)) {
    const count = Array.isArray(value) ? value.length : 1
    const max = num(field.props?.max_files ?? 1)
    if (!Number.isNaN(max) && count > max) return { code: 'max_files', params: { n: max } }
  }

  return null
}

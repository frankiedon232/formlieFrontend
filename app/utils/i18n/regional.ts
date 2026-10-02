import type { DateFormat, NumberFormat, WeekStart } from '#shared/types/onboarding'

/**
 * Regional defaults and pattern formatting for workspace localisation (onboarding, settings,
 * exports). Defaults are suggestions from the country; the admin can always change them.
 */
const YMD = new Set(['CN', 'JP', 'KR', 'TW', 'HU', 'SE', 'LT', 'MN', 'IR', 'CA'])
const DOTTED = new Set([
  'DE',
  'AT',
  'CH',
  'LI',
  'RU',
  'PL',
  'CZ',
  'SK',
  'NO',
  'FI',
  'TR',
  'UA',
  'RO',
  'BG',
  'HR',
  'RS',
  'BY',
  'KZ',
  'EE',
  'LV',
  'IS',
  'DK',
  'AZ',
  'GE',
  'AM',
  'UZ',
])
const MDY = new Set(['US', 'PH', 'PR', 'BZ', 'FM', 'MH', 'PW', 'AS', 'GU', 'VI', 'MP'])

const COMMA_DECIMAL_DOT = new Set([
  'DE',
  'IT',
  'ES',
  'NL',
  'BE',
  'BR',
  'ID',
  'TR',
  'DK',
  'AR',
  'CL',
  'CO',
  'UY',
  'PY',
  'VN',
  'GR',
  'AT',
  'SI',
  'HR',
  'RS',
  'BA',
  'ME',
  'MK',
  'RO',
  'IS',
  'LU',
  'VE',
  'EC',
  'BO',
])
const COMMA_DECIMAL_SPACE = new Set([
  'FR',
  'RU',
  'PL',
  'CZ',
  'SK',
  'SE',
  'NO',
  'FI',
  'UA',
  'ZA',
  'PT',
  'HU',
  'BG',
  'LT',
  'LV',
  'EE',
  'BY',
  'KZ',
  'UZ',
  'GE',
  'AM',
  'AZ',
])
const APOSTROPHE = new Set(['CH', 'LI'])

const SUNDAY = new Set([
  'US',
  'CA',
  'JP',
  'BR',
  'MX',
  'IL',
  'PH',
  'KR',
  'TW',
  'HK',
  'IN',
  'ZA',
  'AU',
  'CO',
  'PE',
  'VE',
  'GT',
  'HN',
  'SV',
  'NI',
  'PA',
  'DO',
  'PR',
  'TH',
  'KE',
  'ZW',
  'BW',
  'PK',
  'BD',
  'ID',
  'SA',
  'YE',
])
const SATURDAY = new Set([
  'AE',
  'EG',
  'IQ',
  'IR',
  'JO',
  'KW',
  'LY',
  'OM',
  'QA',
  'SY',
  'DZ',
  'AF',
  'BH',
  'DJ',
  'SD',
])

export function suggestDateFormat(country: string | null): DateFormat {
  if (!country) return 'DD/MM/YYYY'
  if (MDY.has(country)) return 'MM/DD/YYYY'
  if (YMD.has(country)) return 'YYYY-MM-DD'
  if (DOTTED.has(country)) return 'DD.MM.YYYY'
  return 'DD/MM/YYYY'
}

export function suggestNumberFormat(country: string | null): NumberFormat {
  if (!country) return '1,234.56'
  if (APOSTROPHE.has(country)) return "1'234.56"
  if (COMMA_DECIMAL_DOT.has(country)) return '1.234,56'
  if (COMMA_DECIMAL_SPACE.has(country)) return '1 234,56'
  return '1,234.56'
}

export function suggestWeekStart(country: string | null): WeekStart {
  if (country && SATURDAY.has(country)) return 'saturday'
  if (country && SUNDAY.has(country)) return 'sunday'
  return 'monday'
}

/** Country from the browser language (`en-GB` → `GB`), else null. */
export function browserCountry(): string | null {
  if (typeof navigator === 'undefined') return null
  for (const tag of navigator.languages ?? [navigator.language]) {
    try {
      const region = new Intl.Locale(tag).maximize().region
      if (region && /^[A-Z]{2}$/.test(region)) return region
    } catch {
      // Ignore malformed language tags.
    }
  }
  return null
}

export function browserTimezone(): string {
  try {
    return Intl.DateTimeFormat().resolvedOptions().timeZone || 'UTC'
  } catch {
    return 'UTC'
  }
}

/** Every IANA timezone the browser knows, with its current UTC offset for the picker label. */
export function timezoneOptions(at = new Date()): { value: string; label: string; offset: number }[] {
  const zones: string[] =
    typeof Intl.supportedValuesOf === 'function' ? Intl.supportedValuesOf('timeZone') : ['UTC']
  if (!zones.includes('UTC')) zones.unshift('UTC')
  return zones
    .map(zone => {
      const part = new Intl.DateTimeFormat('en-US', { timeZone: zone, timeZoneName: 'longOffset' })
        .formatToParts(at)
        .find(p => p.type === 'timeZoneName')?.value
      const offsetLabel = !part || part === 'GMT' ? 'GMT+00:00' : part
      const [, sign = '+', hours = '0', minutes = '0'] = /GMT([+-])(\d{2}):?(\d{2})?/.exec(offsetLabel) ?? []
      const offset = (sign === '-' ? -1 : 1) * (Number(hours) * 60 + Number(minutes))
      return { value: zone, label: `(${offsetLabel}) ${zone.replace(/_/g, ' ')}`, offset }
    })
    .sort((a, b) => a.offset - b.offset || a.value.localeCompare(b.value))
}

const pad = (value: number, size = 2) => String(value).padStart(size, '0')

/** Format a date with one of the workspace patterns (calendar digits, not locale words). */
export function formatDatePattern(date: Date, pattern: DateFormat, timeZone?: string): string {
  const parts = Object.fromEntries(
    new Intl.DateTimeFormat('en-US', { timeZone, year: 'numeric', month: 'numeric', day: 'numeric' })
      .formatToParts(date)
      .map(p => [p.type, p.value]),
  )
  const d = pad(Number(parts.day)),
    m = pad(Number(parts.month)),
    y = String(parts.year)
  return pattern === 'MM/DD/YYYY'
    ? `${m}/${d}/${y}`
    : pattern === 'YYYY-MM-DD'
      ? `${y}-${m}-${d}`
      : pattern === 'DD.MM.YYYY'
        ? `${d}.${m}.${y}`
        : `${d}/${m}/${y}`
}

const SEPARATORS: Record<NumberFormat, { group: string; decimal: string }> = {
  '1,234.56': { group: ',', decimal: '.' },
  '1.234,56': { group: '.', decimal: ',' },
  '1 234,56': { group: ' ', decimal: ',' },
  "1'234.56": { group: "'", decimal: '.' },
}

export function formatNumberPattern(value: number, pattern: NumberFormat, decimals = 2): string {
  const { group, decimal } = SEPARATORS[pattern]
  const [whole = '0', fraction] = Math.abs(value).toFixed(decimals).split('.')
  const grouped = whole.replace(/\B(?=(\d{3})+(?!\d))/g, group)
  return `${value < 0 ? '-' : ''}${grouped}${fraction ? decimal + fraction : ''}`
}

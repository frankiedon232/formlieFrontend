/**
 * Global pick lists for language, time zone and currency fields. Names come from the browser's /
 * server's Intl data in the respondent's language, so nothing is hard-coded per country.
 */

/** ISO 639-1 languages (all two-letter codes). */
export const LANGUAGE_CODES = (
  'aa ab af ak am an ar as av ay az ba be bg bi bm bn bo br bs ca ce ch co cr cs cu cv cy da de dv dz ee el en eo es et eu ' +
  'fa ff fi fj fo fr fy ga gd gl gn gu gv ha he hi ho hr ht hu hy hz ia id ie ig ii ik io is it iu ja jv ka kg ki kj kk kl km ' +
  'kn ko kr ks ku kv kw ky la lb lg li ln lo lt lu lv mg mh mi mk ml mn mr ms mt my na nb nd ne ng nl nn no nr nv ny oc oj om ' +
  'or os pa pi pl ps pt qu rm rn ro ru rw sa sc sd se sg si sk sl sm sn so sq sr ss st su sv sw ta te tg th ti tk tl tn to tr ' +
  'ts tt tw ty ug uk ur uz ve vi vo wa wo xh yi yo za zh zu'
).split(' ')

const FALLBACK_ZONES = ['UTC', 'Europe/London', 'Europe/Paris', 'Africa/Lagos', 'Africa/Nairobi', 'Asia/Dubai', 'Asia/Kolkata', 'Asia/Singapore', 'Asia/Tokyo', 'Australia/Sydney', 'America/Sao_Paulo', 'America/New_York', 'America/Los_Angeles']
const FALLBACK_CURRENCIES = ['USD', 'EUR', 'GBP', 'JPY', 'CNY', 'INR', 'NGN', 'KES', 'ZAR', 'BRL', 'AED', 'AUD', 'CAD', 'CHF']

type SupportedKey = 'timeZone' | 'currency'
function supported(key: SupportedKey, fallback: string[]): string[] {
  const intl = Intl as unknown as { supportedValuesOf?: (key: string) => string[] }
  try {
    const values = intl.supportedValuesOf?.(key)
    return values?.length ? values : fallback
  } catch {
    return fallback
  }
}
export const timeZones = () => {
  const zones = supported('timeZone', FALLBACK_ZONES)
  return zones.includes('UTC') ? zones : ['UTC', ...zones]
}
export const currencyCodes = () => supported('currency', FALLBACK_CURRENCIES)

function displayName(locale: string, type: 'language' | 'currency', code: string) {
  try {
    return new Intl.DisplayNames([locale], { type }).of(code) ?? code
  } catch {
    return code
  }
}
/** UTC offset of a zone right now, e.g. "UTC+05:30". */
function offset(zone: string) {
  try {
    const part = new Intl.DateTimeFormat('en-US', { timeZone: zone, timeZoneName: 'longOffset' })
      .formatToParts(new Date())
      .find(p => p.type === 'timeZoneName')?.value
    return part === 'GMT' ? 'UTC' : (part ?? '').replace('GMT', 'UTC')
  } catch {
    return ''
  }
}

export interface PickItem {
  value: string
  label: string
  description?: string
}
const byLabel = (a: PickItem, b: PickItem) => a.label.localeCompare(b.label)

export const languageItems = (locale: string): PickItem[] =>
  LANGUAGE_CODES.map(code => ({ value: code, label: displayName(locale, 'language', code), description: code })).sort(byLabel)
export const currencyItems = (locale: string): PickItem[] =>
  currencyCodes().map(code => ({ value: code, label: displayName(locale, 'currency', code), description: code })).sort(byLabel)
export const timeZoneItems = (): PickItem[] =>
  timeZones().map(zone => ({ value: zone, label: zone.replace(/_/g, ' '), description: offset(zone) }))

export const isLanguageCode = (value: string) => LANGUAGE_CODES.includes(value)
export const isTimeZone = (value: string) => {
  if (value === 'UTC') return true
  try {
    new Intl.DateTimeFormat('en', { timeZone: value })
    return true
  } catch {
    return false
  }
}
export const isCurrencyCode = (value: string) => /^[A-Z]{3}$/.test(value) && currencyCodes().includes(value)

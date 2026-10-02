/**
 * Locale-aware formatting (CLAUDE.md rule 17) via Intl, following the active language.
 * Tenant timezone/currency defaults arrive with Settings → Localisation (F13).
 */
const RELATIVE_UNITS: [Intl.RelativeTimeFormatUnit, number][] = [
  ['year', 31_536_000],
  ['month', 2_592_000],
  ['week', 604_800],
  ['day', 86_400],
  ['hour', 3_600],
  ['minute', 60],
  ['second', 1],
]

export function useFormat() {
  const { current } = useAppLocale()
  const lang = computed(() => current.value.language)

  const toDate = (value: string | number | Date) => (value instanceof Date ? value : new Date(value))

  function date(
    value: string | number | Date | null | undefined,
    style: Intl.DateTimeFormatOptions['dateStyle'] = 'medium',
  ) {
    if (value == null || value === '') return ''
    return new Intl.DateTimeFormat(lang.value, { dateStyle: style }).format(toDate(value))
  }

  function dateTime(value: string | number | Date | null | undefined) {
    if (value == null || value === '') return ''
    return new Intl.DateTimeFormat(lang.value, { dateStyle: 'medium', timeStyle: 'short' }).format(
      toDate(value),
    )
  }

  /** "3 minutes ago", "in 2 days" — falls back to "now" under 5 s. */
  function relative(value: string | number | Date | null | undefined, now = Date.now()) {
    if (value == null || value === '') return ''
    const seconds = Math.round((toDate(value).getTime() - now) / 1000)
    const formatter = new Intl.RelativeTimeFormat(lang.value, { numeric: 'auto' })
    if (Math.abs(seconds) < 5) return formatter.format(0, 'second')
    const [unit, size] = RELATIVE_UNITS.find(([, s]) => Math.abs(seconds) >= s) ?? ['second', 1]
    return formatter.format(Math.round(seconds / size), unit)
  }

  function number(value: number | null | undefined, options?: Intl.NumberFormatOptions) {
    if (value == null || Number.isNaN(value)) return ''
    return new Intl.NumberFormat(lang.value, options).format(value)
  }

  const compact = (value: number | null | undefined) =>
    number(value, { notation: 'compact', maximumFractionDigits: 1 })
  const percent = (value: number | null | undefined, digits = 0) =>
    number(value, { style: 'percent', maximumFractionDigits: digits })
  const currency = (value: number | null | undefined, code = 'USD') =>
    number(value, { style: 'currency', currency: code })

  function fileSize(bytes: number | null | undefined) {
    if (bytes == null) return ''
    const units = ['byte', 'kilobyte', 'megabyte', 'gigabyte'] as const
    let size = bytes
    let index = 0
    while (size >= 1024 && index < units.length - 1) {
      size /= 1024
      index++
    }
    return number(size, { style: 'unit', unit: units[index], unitDisplay: 'short', maximumFractionDigits: 1 })
  }

  return { date, dateTime, relative, number, compact, percent, currency, fileSize }
}

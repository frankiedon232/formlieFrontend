/**
 * Locale-aware formatting (CLAUDE.md rule 17) via Intl, following the active language, with the
 * workspace's own language and region (Settings → Language and region, F14): its time zone for dates
 * and times, its date format for short dates, its group / decimal signs for numbers, its currency.
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
  const { locale: workspace } = useWorkspaceLocale()
  // A person's own time zone and date format (My profile, F16 M5) come before the workspace's
  const session = useSession()
  const timeZone = computed(() => session.user.value?.time_zone || workspace.value?.timezone)
  const dateFormat = computed(() => session.user.value?.date_format || workspace.value?.date_format)

  const toDate = (value: string | number | Date) => (value instanceof Date ? value : new Date(value))

  function date(
    value: string | number | Date | null | undefined,
    style: Intl.DateTimeFormatOptions['dateStyle'] = 'medium',
  ) {
    if (value == null || value === '') return ''
    // Short dates follow the workspace's date format (31/12/2026, 2026-12-31…)
    if (style === 'short' && dateFormat.value) return formatDatePattern(toDate(value), dateFormat.value, timeZone.value ?? 'UTC')
    return new Intl.DateTimeFormat(lang.value, { dateStyle: style, timeZone: timeZone.value }).format(toDate(value))
  }

  function dateTime(value: string | number | Date | null | undefined) {
    if (value == null || value === '') return ''
    return new Intl.DateTimeFormat(lang.value, { dateStyle: 'medium', timeStyle: 'short', timeZone: timeZone.value }).format(toDate(value))
  }

  /** "3 minutes ago", "in 2 days", falls back to "now" under 5 s. */
  function relative(value: string | number | Date | null | undefined, now = Date.now()) {
    if (value == null || value === '') return ''
    const seconds = Math.round((toDate(value).getTime() - now) / 1000)
    const formatter = new Intl.RelativeTimeFormat(lang.value, { numeric: 'auto' })
    if (Math.abs(seconds) < 5) return formatter.format(0, 'second')
    const [unit, size] = RELATIVE_UNITS.find(([, s]) => Math.abs(seconds) >= s) ?? ['second', 1]
    return formatter.format(Math.round(seconds / size), unit)
  }

  const dayKey = (value: Date) => new Intl.DateTimeFormat('en-CA', { timeZone: timeZone.value }).format(value)
  /** Compact moment: "14:32" today, "Yesterday 14:32", "Mon 14:32" this week, else "3 Oct, 14:32" (or with the year). */
  function moment(value: string | number | Date | null | undefined, now = Date.now()) {
    if (value == null || value === '') return ''
    const at = toDate(value)
    const time = new Intl.DateTimeFormat(lang.value, { timeStyle: 'short', timeZone: timeZone.value }).format(at)
    const days = Math.round((Date.parse(dayKey(new Date(now))) - Date.parse(dayKey(at))) / 86_400_000)
    if (days === 0) return time
    if (days === 1) {
      const word = new Intl.RelativeTimeFormat(lang.value, { numeric: 'auto' }).format(-1, 'day')
      return `${word.charAt(0).toLocaleUpperCase(lang.value)}${word.slice(1)} ${time}`
    }
    const options: Intl.DateTimeFormatOptions = days > 1 && days < 7 ? { weekday: 'short' } : { day: 'numeric', month: 'short', ...(new Date(now).getFullYear() !== at.getFullYear() ? { year: 'numeric' } : {}) }
    return `${new Intl.DateTimeFormat(lang.value, { ...options, timeZone: timeZone.value }).format(at)}, ${time}`
  }

  /** Compact length of time: "45s", "25m", "1h 20m", "2d 3h" (narrow units in the active language). */
  function span(ms: number | null | undefined) {
    if (ms == null || ms < 0) return ''
    const unit = (n: number, name: string) => number(n, { style: 'unit', unit: name, unitDisplay: 'narrow' })
    const seconds = Math.round(ms / 1000)
    if (seconds < 60) return unit(seconds, 'second')
    const minutes = Math.round(seconds / 60)
    if (minutes < 60) return unit(minutes, 'minute')
    const hours = Math.floor(minutes / 60)
    if (hours < 24) return [unit(hours, 'hour'), minutes % 60 ? unit(minutes % 60, 'minute') : ''].filter(Boolean).join(' ')
    return [unit(Math.floor(hours / 24), 'day'), hours % 24 ? unit(hours % 24, 'hour') : ''].filter(Boolean).join(' ')
  }

  function number(value: number | null | undefined, options?: Intl.NumberFormatOptions) {
    if (value == null || Number.isNaN(value)) return ''
    const formatter = new Intl.NumberFormat(lang.value, options)
    const signs = workspace.value ? NUMBER_SIGNS[workspace.value.number_format] : null
    if (!signs) return formatter.format(value)
    // The workspace's group and decimal signs, the rest (words, symbols) in the person's language
    return formatter
      .formatToParts(value)
      .map(part => (part.type === 'group' ? signs.group : part.type === 'decimal' ? signs.decimal : part.value))
      .join('')
  }

  const compact = (value: number | null | undefined) =>
    number(value, { notation: 'compact', maximumFractionDigits: 1 })
  const percent = (value: number | null | undefined, digits = 0) =>
    number(value, { style: 'percent', maximumFractionDigits: digits })
  const currency = (value: number | null | undefined, code = workspace.value?.currency ?? 'USD') =>
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

  return { date, dateTime, moment, span, relative, number, compact, percent, currency, fileSize }
}

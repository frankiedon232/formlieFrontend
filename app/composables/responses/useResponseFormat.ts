import type { BadgeProps } from '@nuxt/ui'
import type { ResponseStatus } from '#shared/types/responses'
import type { FormField } from '#shared/utils/forms/build'

/** Review status look (F11): badge colour, chart colour, icon. Colour is always named next to it. */
export const RESPONSE_STATUS_META: Record<ResponseStatus, { color: BadgeProps['color']; fill: string; icon: string }> = {
  new: { color: 'info', fill: 'bg-info', icon: 'i-lucide-sparkle' },
  reviewed: { color: 'neutral', fill: 'bg-inverted/35', icon: 'i-lucide-eye' },
  approved: { color: 'success', fill: 'bg-success', icon: 'i-lucide-circle-check' },
  rejected: { color: 'error', fill: 'bg-error', icon: 'i-lucide-circle-x' },
}

/** Question types that make a good table column (short, one line). */
const COLUMN_TYPES = new Set([
  'short_text', 'number', 'currency', 'percentage', 'date', 'time', 'datetime', 'dropdown', 'radio', 'checkbox', 'multi_select',
  'toggle', 'rating', 'scale', 'slider', 'country', 'language', 'currency_code', 'phone', 'url', 'hidden', 'calculated', 'timezone',
])
/** Already in the Respondent column. */
const PERSON = /^(your\s+)?(full\s+|first\s+|last\s+|family\s+|given\s+)?name$|e-?mail/i
export const goodColumn = (field: FormField) => COLUMN_TYPES.has(field.type) && !PERSON.test((field.label ?? '').trim())

const dateOnly = (value: unknown) => (typeof value === 'string' && /^\d{4}-\d{2}-\d{2}$/.test(value) ? `${value}T12:00:00` : (value as string))

/**
 * Any answer as readable text, in the person's language (F11 table, grid, detail, summaries):
 * choices by their label, dates and numbers formatted, addresses on one line, files by name.
 */
export function useResponseFormat() {
  const { t } = useI18n()
  const { current } = useAppLocale()
  const { number, date, dateTime, currency, fileSize } = useFormat()
  const regions = computed(() => new Intl.DisplayNames(current.value.language, { type: 'region' }))
  const tongues = computed(() => new Intl.DisplayNames(current.value.language, { type: 'language' }))
  const name = (names: Intl.DisplayNames, code: unknown) => {
    try {
      return names.of(String(code)) ?? String(code)
    } catch {
      return String(code)
    }
  }

  function text(field: FormField | undefined, value: unknown): string {
    if (value == null || value === '' || (Array.isArray(value) && !value.length)) return ''
    const options = new Map((field?.options ?? []).map(option => [option.value, option.label]))
    const label = (v: unknown) => options.get(String(v)) ?? String(v)
    const p = (field?.props ?? {}) as Record<string, unknown>
    const object = (value && typeof value === 'object' ? value : {}) as Record<string, unknown>
    switch (field?.type) {
      case 'checkbox':
      case 'multi_select':
        return (Array.isArray(value) ? value : [value]).map(label).join(', ')
      case 'radio':
      case 'dropdown':
        return label(value)
      case 'ranking':
        return (Array.isArray(value) ? value : []).map((v, i) => `${i + 1}. ${label(v)}`).join('   ')
      case 'matrix':
        return Object.entries(object).map(([row, v]) => `${row}: ${label(v)}`).join(' · ')
      case 'toggle':
        return value ? t('responses.answer.yes') : t('responses.answer.no')
      case 'consent':
        return value ? t('responses.answer.agreed') : ''
      case 'rating':
        return `${number(Number(value))} / ${Number(p.max ?? 5)}`
      case 'currency':
        return currency(Number(value), String(p.currency ?? 'USD'))
      case 'percentage':
        return `${number(Number(value))}%`
      case 'number':
      case 'scale':
      case 'slider':
        return number(Number(value))
      case 'date':
        return date(dateOnly(value))
      case 'datetime':
        return dateTime(String(value))
      case 'date_range':
        return [date(dateOnly(object.from)), date(dateOnly(object.to))].filter(Boolean).join(' → ')
      case 'duration':
        return t('responses.answer.duration', { h: Number(object.hours ?? 0), m: Number(object.minutes ?? 0) })
      case 'full_name':
        return [object.title, object.first, object.middle, object.last].filter(Boolean).join(' ')
      case 'address':
        return [object.line1, object.line2, object.city, object.region, object.postal_code, object.country && name(regions.value, object.country)].filter(Boolean).join(', ')
      case 'country':
        return name(regions.value, value)
      case 'language':
        return name(tongues.value, value)
      case 'file_upload':
      case 'image_upload': {
        const files = (Array.isArray(value) ? value : []) as { name?: string; size?: number }[]
        return files.map(file => `${file.name ?? ''}${file.size ? ` (${fileSize(file.size)})` : ''}`).join(', ')
      }
      case 'signature':
        return t('responses.answer.signed')
      case 'rich_text':
        return String(value).replace(/<[^>]*>/g, ' ').replace(/\s+/g, ' ').trim()
      default:
        return typeof value === 'object' ? Object.values(object).filter(Boolean).join(', ') : String(value)
    }
  }

  /** "2 min 05 s" for a fill-in time. */
  const duration = (seconds: number | null | undefined) =>
    seconds == null ? '' : seconds < 60 ? t('responses.time.seconds', { n: seconds }) : t('responses.time.minutes', { m: Math.floor(seconds / 60), s: String(seconds % 60).padStart(2, '0') })

  return { text, duration }
}

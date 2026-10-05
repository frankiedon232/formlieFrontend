/**
 * An answer as plain text for export files (F11 M3: CSV, Excel, PDF). Unlike the portal's display
 * (useResponseFormat, in the person's language), files use stable, sortable values: ISO dates,
 * numbers without grouping, choices by their label, several picks joined with "; ", addresses and
 * names on one line, files by name. Yes / No words come from the caller (the file's language).
 */
import type { FormField } from './build'

export interface AnswerTextWords {
  yes: string
  no: string
  agreed: string
}

const EN: AnswerTextWords = { yes: 'Yes', no: 'No', agreed: 'Agreed' }

export function answerText(field: Pick<FormField, 'type' | 'options' | 'props'> | undefined, value: unknown, words: AnswerTextWords = EN): string {
  if (value == null || value === '' || (Array.isArray(value) && !value.length)) return ''
  const options = new Map((field?.options ?? []).map(option => [option.value, option.label]))
  const label = (v: unknown) => options.get(String(v)) ?? String(v)
  const object = (value && typeof value === 'object' && !Array.isArray(value) ? value : {}) as Record<string, unknown>
  switch (field?.type) {
    case 'checkbox':
    case 'multi_select':
      return (Array.isArray(value) ? value : [value]).map(label).join('; ')
    case 'radio':
    case 'dropdown':
      return label(value)
    case 'ranking':
      return (Array.isArray(value) ? value : []).map((v, i) => `${i + 1}. ${label(v)}`).join('; ')
    case 'matrix':
      return Object.entries(object)
        .map(([row, v]) => `${row}: ${label(v)}`)
        .join('; ')
    case 'toggle':
      return value === true || value === 'true' ? words.yes : words.no
    case 'consent':
      return value ? words.agreed : ''
    case 'date_range':
      return [object.from, object.to].filter(Boolean).join(' / ')
    case 'duration':
      return `${Number(object.hours ?? 0)}h ${Number(object.minutes ?? 0)}m`
    case 'full_name':
      return [object.title, object.first, object.middle, object.last].filter(Boolean).join(' ')
    case 'address':
      return [object.line1, object.line2, object.city, object.region, object.postal_code, object.country].filter(Boolean).join(', ')
    case 'file_upload':
    case 'image_upload':
      return (Array.isArray(value) ? value : [])
        .map(file => (file && typeof file === 'object' ? String((file as { name?: string }).name ?? '') : String(file)))
        .filter(Boolean)
        .join('; ')
    case 'signature':
      return words.agreed
    case 'rich_text':
      return String(value)
        .replace(/<[^>]*>/g, ' ')
        .replace(/\s+/g, ' ')
        .trim()
    default:
      if (Array.isArray(value)) return value.map(String).join('; ')
      if (typeof value === 'object') return Object.values(object).filter(part => part != null && part !== '').map(String).join(', ')
      return String(value)
  }
}

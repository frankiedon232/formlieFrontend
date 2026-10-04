/**
 * Insights for the Responses pages (F11): totals, the trend for a period against the period before,
 * review status, channels, languages, time to fill in, and a summary per question (how often each
 * choice was picked, average ratings, number ranges, the latest text answers). Same numbers for the
 * form overview's trend, so both pages always agree.
 */
import type { QuestionInsight, ResponseInsights, ResponseStatus } from '#shared/types/responses'
import { allFields, type FormField } from '#shared/utils/forms/build'
import { isInputField } from '#shared/utils/forms/fields'
import { answersOf, responseSchema, type IndexedResponse } from './responseData'
import type { StoredForm } from './formStore'

const DAY = 86_400_000
const dayOf = (ms: number) => new Date(ms).toISOString().slice(0, 10)

/** The period asked for (`from` / `to` as dates), else the last 30 days up to today. */
export function periodOf(query: Record<string, unknown>) {
  const today = Date.parse(dayOf(Date.now()))
  const to = typeof query.to === 'string' && query.to ? Date.parse(query.to) : today
  const from = typeof query.from === 'string' && query.from ? Date.parse(query.from) : to - 29 * DAY
  return { from: Math.min(from, to), to: Math.max(from, to) }
}

const median = (values: number[]) => {
  if (!values.length) return null
  const sorted = [...values].sort((a, b) => a - b)
  const mid = Math.floor(sorted.length / 2)
  return sorted.length % 2 ? sorted[mid]! : (sorted[mid - 1]! + sorted[mid]!) / 2
}
const round = (n: number, digits = 1) => Math.round(n * 10 ** digits) / 10 ** digits

const CHOICE = new Set(['radio', 'dropdown', 'checkbox', 'multi_select', 'toggle', 'country', 'language', 'currency_code'])
const RATING = new Set(['rating', 'scale', 'slider'])
const NUMBER = new Set(['number', 'currency', 'percentage'])
const TEXT = new Set(['short_text', 'long_text'])

function questionInsight(field: FormField, rows: { entry: IndexedResponse; data: Record<string, unknown> }[]): QuestionInsight {
  const base = { key: field.key, label: field.label?.trim() || field.key, type: field.type }
  const values = rows.map(row => ({ entry: row.entry, value: row.data[field.key] })).filter(item => item.value != null && item.value !== '' && !(Array.isArray(item.value) && !item.value.length))
  const answered = values.length
  // Calculated questions: numbers summarised as numbers, words ("Promoter") as choices.
  const calculated = field.type === 'calculated'
  const numeric = calculated && values.length > 0 && values.every(item => typeof item.value === 'number')
  if (CHOICE.has(field.type) || (calculated && !numeric)) {
    const counts = new Map<string, number>()
    for (const { value } of values) for (const one of Array.isArray(value) ? value : [value]) counts.set(String(one), (counts.get(String(one)) ?? 0) + 1)
    const known = field.type === 'toggle' ? [{ value: 'true', label: '' }, { value: 'false', label: '' }] : (field.options ?? []).map(option => ({ value: option.value, label: option.label }))
    const options = known.length
      ? known.map(option => ({ ...option, count: counts.get(option.value) ?? 0 }))
      : [...counts].map(([value, count]) => ({ value, label: value, count })).sort((a, b) => b.count - a.count).slice(0, 8)
    return { ...base, answered, kind: 'choice', multiple: field.type === 'checkbox' || field.type === 'multi_select', options }
  }
  if (RATING.has(field.type)) {
    const numbers = values.map(item => Number(item.value)).filter(n => !Number.isNaN(n))
    const p = (field.props ?? {}) as Record<string, unknown>
    const min = field.type === 'rating' ? 1 : Number(p.min ?? 0)
    const max = Number(p.max ?? (field.type === 'rating' ? 5 : field.type === 'scale' ? 10 : 100))
    // Sliders: ten even steps; ratings and scales: every value.
    const step = field.type === 'slider' ? Math.max(1, Math.ceil((max - min + 1) / 10)) : 1
    const distribution: { value: number; count: number }[] = []
    for (let value = min; value <= max; value += step) distribution.push({ value, count: numbers.filter(n => n >= value && n < value + step).length })
    return { ...base, answered, kind: 'rating', average: numbers.length ? round(numbers.reduce((a, b) => a + b, 0) / numbers.length) : 0, min, max, distribution }
  }
  if (NUMBER.has(field.type) || numeric) {
    const numbers = values.map(item => Number(item.value)).filter(n => !Number.isNaN(n))
    if (!numbers.length) return { ...base, answered, kind: 'other' }
    return { ...base, answered, kind: 'number', average: round(numbers.reduce((a, b) => a + b, 0) / numbers.length, 2), min: Math.min(...numbers), max: Math.max(...numbers), median: median(numbers)! }
  }
  if (TEXT.has(field.type)) {
    const latest = values.filter(item => typeof item.value === 'string').slice(0, 5).map(item => ({ id: item.entry.id, value: String(item.value).slice(0, 280), at: new Date(item.entry.at).toISOString() }))
    return { ...base, answered, kind: 'text', latest }
  }
  return { ...base, answered, kind: 'other' }
}

/**
 * Insights for a list of responses (newest first). `form` = per-form insights with completion and
 * a summary per question; without it, the inbox (with the busiest forms instead).
 */
export function insightsOf(entries: { form: StoredForm; entry: IndexedResponse }[], query: Record<string, unknown>, form?: StoredForm): ResponseInsights {
  const { from, to } = periodOf(query)
  const end = to + DAY
  const span = end - from
  const inPeriod = entries.filter(({ entry }) => entry.at >= from && entry.at < end)
  const previous = entries.filter(({ entry }) => entry.at >= from - span && entry.at < from).length
  const daily = Array.from({ length: Math.round(span / DAY) }, (_, i) => ({ date: dayOf(from + i * DAY), count: 0 }))
  for (const { entry } of inPeriod) daily[Math.floor((entry.at - from) / DAY)]!.count++

  const status: Record<ResponseStatus, number> = { new: 0, reviewed: 0, approved: 0, rejected: 0 }
  const channels = { link: 0, embed: 0, api: 0 }
  const languages = new Map<string, number>()
  for (const { entry } of entries) status[entry.status]++
  for (const { entry } of inPeriod) {
    channels[entry.channel]++
    languages.set(entry.language, (languages.get(entry.language) ?? 0) + 1)
  }

  let questions: QuestionInsight[] = []
  if (form) {
    const schema = responseSchema(form)
    const rows = inPeriod.map(({ entry }) => ({ entry, data: answersOf(form, entry) }))
    questions = schema ? allFields(schema).filter(field => isInputField(field.type) && field.type !== 'hidden' && field.type !== 'payment').map(field => questionInsight(field, rows)) : []
  }
  const busiest = new Map<string, { id: string; name: string; count: number }>()
  if (!form)
    for (const { form: owner } of inPeriod) {
      const item = busiest.get(owner.id) ?? { id: owner.id, name: owner.name, count: 0 }
      item.count++
      busiest.set(owner.id, item)
    }

  return {
    total: entries.length,
    new: status.new,
    period: { from: dayOf(from), to: dayOf(to), count: inPeriod.length, previous },
    daily,
    status,
    channels,
    languages: [...languages].map(([code, count]) => ({ code, count })).sort((a, b) => b.count - a.count).slice(0, 6),
    median_seconds: median(inPeriod.map(({ entry }) => entry.duration_seconds).filter((n): n is number => n != null)),
    // Not measured yet (forms made in the portal have no visit tracking until analytics, F18) = null.
    completion_rate: form?.completion_rate ? form.completion_rate : null,
    last_at: entries[0] ? new Date(entries[0].entry.at).toISOString() : null,
    questions,
    top_forms: [...busiest.values()].sort((a, b) => b.count - a.count).slice(0, 5),
    schema: form ? responseSchema(form) : null,
  }
}

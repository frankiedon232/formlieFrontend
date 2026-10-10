/**
 * The mock assistant's analysis (F19 M4), built in (no outside service, decided 2026-10-10):
 *
 *   textOf / themesOf / sentimentOf   word lists find what written answers are about and their tone
 *   analyse                           a period against the one before: responses, tone, themes with
 *                                     examples, average ratings, top choices, and what stands out
 *   ask                               a question in plain words → count, top answers, average or trend,
 *                                     with the question, period and filters it understood
 *   summarise                         one response in a few lines
 *
 * The backend's model replaces it with the same answer shapes.
 */
import type { AiAnalysis, AiAnswer, AiNote, AiSentiment, AiTheme } from '#shared/types/ai'
import { allFields, type FormField } from '#shared/utils/forms/build'
import { periodIn, sentimentOf, textOf, themesOf } from './textAnalysis'
import { isInputField } from '#shared/utils/forms/fields'
import { answersOf, responseSchema, type IndexedResponse } from '../data/responseData'
import type { StoredForm } from '../data/formStore'

const DAY = 86_400_000
const isoDay = (ms: number) => new Date(ms).toISOString().slice(0, 10)
const round = (n: number, digits = 1) => Math.round(n * 10 ** digits) / 10 ** digits

const emptySentiment = (): AiSentiment => ({ positive: 0, neutral: 0, negative: 0 })

interface Row {
  entry: IndexedResponse
  data: Record<string, unknown>
}

function rowsIn(form: StoredForm, entries: IndexedResponse[], from: number, to: number): Row[] {
  return entries.filter(entry => entry.at >= from && entry.at < to + DAY).map(entry => ({ entry, data: answersOf(form, entry) }))
}

const labelOf = (field: FormField, value: unknown): string => {
  if (value === true) return 'Yes'
  if (value === false) return 'No'
  const option = field.options?.find(item => item.value === value)
  return option?.label ?? String(value)
}

const RATING = new Set(['rating', 'scale', 'slider'])
const CHOICE = new Set(['radio', 'dropdown', 'checkbox', 'multi_select', 'toggle', 'country', 'language'])
const maxOf = (field: FormField) => Number(field.props?.max) || (field.type === 'scale' ? 10 : field.type === 'slider' ? 100 : 5)
const average = (rows: Row[], field: FormField) => {
  const values = rows.map(row => row.data[field.key]).filter((value): value is number => typeof value === 'number')
  return values.length ? round(values.reduce((a, b) => a + b, 0) / values.length) : null
}

/** A period's analysis against the period of the same length before it. */
export function analyse(form: StoredForm, entries: IndexedResponse[], from: number, to: number, mask: (text: string) => string): Omit<AiAnalysis, 'request_id' | 'credits'> {
  const schema = responseSchema(form)
  const fields = schema ? allFields(schema).filter(field => isInputField(field.type)) : []
  const length = to - from + DAY
  const rows = rowsIn(form, entries, from, to)
  const before = rowsIn(form, entries, from - length, from - DAY)

  const tone = (list: Row[]) => {
    const totals = emptySentiment()
    for (const row of list) for (const text of textOf(fields, row.data)) totals[sentimentOf(text)] += 1
    return totals
  }
  const sentiment = tone(rows)
  const themes = new Map<AiTheme, { count: number; positive: number; negative: number; examples: string[] }>()
  let textAnswers = 0
  for (const row of rows)
    for (const text of textOf(fields, row.data)) {
      textAnswers += 1
      const mood = sentimentOf(text)
      for (const key of themesOf(text)) {
        const item = themes.get(key) ?? { count: 0, positive: 0, negative: 0, examples: [] }
        item.count += 1
        if (mood === 'positive') item.positive += 1
        if (mood === 'negative') item.negative += 1
        if (item.examples.length < 3 && !item.examples.includes(mask(text))) item.examples.push(mask(text))
        themes.set(key, item)
      }
    }
  const themeList = [...themes.entries()]
    .map(([key, item]) => ({ key, ...item, share: textAnswers ? round((item.count / textAnswers) * 100, 0) : 0 }))
    .sort((a, b) => Number(a.key === 'other') - Number(b.key === 'other') || b.count - a.count)
    .slice(0, 8)

  const ratings = fields
    .filter(field => RATING.has(field.type))
    .map(field => ({ key: field.key, label: field.label, average: average(rows, field), previous: average(before, field), max: maxOf(field) }))
    .filter((item): item is { key: string; label: string; average: number; previous: number | null; max: number } => item.average !== null)
  const choices = fields
    .filter(field => CHOICE.has(field.type))
    .slice(0, 4)
    .flatMap(field => {
      const counts = new Map<string, number>()
      let answered = 0
      for (const row of rows) {
        const value = row.data[field.key]
        if (value == null || value === '') continue
        answered += 1
        for (const item of Array.isArray(value) ? value : [value]) counts.set(labelOf(field, item), (counts.get(labelOf(field, item)) ?? 0) + 1)
      }
      const top = [...counts.entries()].sort((a, b) => b[1] - a[1])[0]
      return top && answered ? [{ key: field.key, label: field.label, top: top[0], share: round((top[1] / answered) * 100, 0) }] : []
    })

  const days = Math.round(length / DAY)
  const daily = Array.from({ length: Math.min(days, 92) }, (_, index) => {
    const date = isoDay(to - (Math.min(days, 92) - 1 - index) * DAY)
    return { date, count: rows.filter(row => isoDay(row.entry.at) === date).length }
  })

  const findings: AiNote[] = []
  if (rows.length < 5) findings.push({ code: 'few_responses', params: { n: rows.length } })
  if (before.length && rows.length) {
    const change = Math.round(((rows.length - before.length) / before.length) * 100)
    if (Math.abs(change) >= 10) findings.push({ code: change > 0 ? 'responses_up' : 'responses_down', params: { n: Math.abs(change) } })
  }
  const busiest = [...daily].sort((a, b) => b.count - a.count)[0]
  if (busiest && busiest.count >= 3) findings.push({ code: 'busiest_day', params: { day: busiest.date, n: busiest.count } })
  for (const rating of ratings)
    if (rating.previous !== null && Math.abs(rating.average - rating.previous) >= 0.3)
      findings.push({ code: rating.average > rating.previous ? 'rating_up' : 'rating_down', params: { label: rating.label, from: rating.previous, to: rating.average } })
  // Criticised = more negative than positive answers; praised = the other way round (a theme is never both)
  const worst = themeList.filter(item => item.key !== 'other' && item.negative >= 2 && item.negative >= item.positive).sort((a, b) => b.negative - a.negative)[0]
  if (worst) findings.push({ code: 'theme_negative', theme: worst.key, params: { n: worst.negative } })
  const best = themeList.filter(item => item.key !== 'other' && item.positive >= 2 && item.positive > item.negative).sort((a, b) => b.positive - a.positive)[0]
  if (best) findings.push({ code: 'theme_positive', theme: best.key, params: { n: best.positive } })
  if (!textAnswers) findings.push({ code: 'no_text' })

  return {
    form: { id: form.id, name: form.name },
    period: { from: isoDay(from), to: isoDay(to) },
    previous: { from: isoDay(from - length), to: isoDay(from - DAY) },
    totals: { responses: rows.length, previous: before.length, text_answers: textAnswers },
    daily,
    sentiment,
    previous_sentiment: tone(before),
    themes: themeList,
    ratings,
    choices,
    findings,
  }
}

// ── Questions in plain words ──────────────────────────────────────────────────────────

const STOP = new Set('a an and are as at be by did do does for from how i in is it many me most much my of on or our per the their there this to was we were what when which who with you your any all average mean number count responses response answers answer people times total last this month week year day days today yesterday said say'.split(' '))

const contentWords = (text: string) => text.toLowerCase().replace(/[^\p{L}\p{N}\s]/gu, ' ').split(/\s+/).map(word => word.replace(/(?<!s)s$/, '')).filter(word => word.length > 2 && !STOP.has(word))

/** The question the form asks that the person most likely means. */
function fieldIn(question: string, fields: FormField[], prefer?: (field: FormField) => boolean): FormField | null {
  const asked = new Set(contentWords(question))
  const scored = fields
    .map(field => ({ field, score: contentWords(field.label).filter(word => asked.has(word)).length + (field.options ?? []).filter(option => question.toLowerCase().includes(option.label.toLowerCase())).length * 2 }))
    .filter(item => item.score > 0)
    .sort((a, b) => b.score - a.score || Number(prefer?.(b.field) ?? 0) - Number(prefer?.(a.field) ?? 0))
  return scored[0]?.field ?? null
}

const STATUSES = ['new', 'reviewed', 'approved', 'rejected'] as const

export function ask(form: StoredForm, entries: IndexedResponse[], question: string): Omit<AiAnswer, 'request_id' | 'credits' | 'question'> {
  const schema = responseSchema(form)
  const fields = schema ? allFields(schema).filter(field => isInputField(field.type) && field.type !== 'hidden') : []
  const q = question.toLowerCase()
  const notes: AiNote[] = []
  const filters: AiAnswer['filters'] = []
  const period = periodIn(question)
  let list = entries
  if (period) {
    list = list.filter(entry => entry.at >= period.from && entry.at < period.to + DAY)
    // The app shows the dates from `period`
    filters.push({ kind: 'period', label: 'period', value: period.label })
  } else notes.push({ code: 'period_default' })
  const status = STATUSES.find(item => new RegExp(`\\b${item}\\b`).test(q))
  if (status) {
    list = list.filter(entry => entry.status === status)
    filters.push({ kind: 'status', label: 'status', value: status })
  }
  const rows = list.map(entry => ({ entry, data: answersOf(form, entry) }))

  const wantsAverage = /\b(average|mean|avg|typical)\b/.test(q)
  const wantsTrend = /\b(per (day|week|month)|by (day|week|month)|each (day|week|month)|trend|over time|monthly|weekly|daily)\b/.test(q)
  const wantsTop = /\b(most|top|which|popular|common|best|worst|favourite|favorite|breakdown|split)\b/.test(q)
  const numeric = (field: FormField) => RATING.has(field.type) || ['number', 'currency', 'percentage'].includes(field.type)

  // An answer named in the question filters the responses ("how many said Yes", "requests from the Riverside office")
  const named = fields.flatMap(field => (field.options ?? []).filter(option => option.label.length > 2 && new RegExp(`\\b${option.label.toLowerCase().replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}\\b`).test(q)).map(option => ({ field, option })))[0]
  const filtered = named && !wantsTop ? rows.filter(row => [row.data[named.field.key]].flat().includes(named.option.value)) : rows
  if (named && !wantsTop) filters.push({ kind: 'answer', label: named.field.label, value: named.option.label })

  if (wantsTrend) {
    const byMonth = /\bmonth/.test(q) || !/\b(day|week)/.test(q)
    const bucket = (at: number) => (byMonth ? isoDay(at).slice(0, 7) : /\bweek/.test(q) ? isoDay(at - ((new Date(at).getUTCDay() + 6) % 7) * DAY) : isoDay(at))
    const field = wantsAverage ? fieldIn(question, fields.filter(numeric)) : null
    const groups = new Map<string, Row[]>()
    for (const row of filtered) groups.set(bucket(row.entry.at), [...(groups.get(bucket(row.entry.at)) ?? []), row])
    const keys = [...groups.keys()].sort()
    const rowsOut = keys.map(key => {
      const items = groups.get(key)!
      const value = field ? (average(items, field) ?? 0) : items.length
      return { label: key, count: value, share: 0 }
    })
    const top = Math.max(1, ...rowsOut.map(row => row.count))
    return { kind: 'trend', value: null, field: field ? { key: field.key, label: field.label } : null, rows: rowsOut.map(row => ({ ...row, share: Math.round((row.count / top) * 100) })), filters, period: period ? { from: isoDay(period.from), to: isoDay(period.to) } : null, notes }
  }

  if (wantsAverage) {
    const field = fieldIn(question, fields.filter(numeric)) ?? fields.find(numeric) ?? null
    if (!field) return { kind: 'average', value: null, field: null, rows: [], filters, period: period ? { from: isoDay(period.from), to: isoDay(period.to) } : null, notes: [...notes, { code: 'no_field' }] }
    if (!fieldIn(question, fields.filter(numeric))) notes.push({ code: 'field_guess', params: { label: field.label } })
    return { kind: 'average', value: average(filtered, field), field: { key: field.key, label: field.label }, rows: [], filters, period: period ? { from: isoDay(period.from), to: isoDay(period.to) } : null, notes }
  }

  const namedChoice = wantsTop ? (named?.field ?? fieldIn(question, fields.filter(field => CHOICE.has(field.type)))) : null
  // No question named: the form's first choice question, and the answer says so
  const choiceField = wantsTop ? (namedChoice ?? fields.find(field => CHOICE.has(field.type)) ?? null) : null
  if (wantsTop && choiceField && !namedChoice) notes.push({ code: 'field_guess', params: { label: choiceField.label } })
  if (wantsTop && choiceField) {
    const counts = new Map<string, number>()
    let answered = 0
    for (const row of filtered) {
      const value = row.data[choiceField.key]
      if (value == null || value === '') continue
      answered += 1
      for (const item of [value].flat()) counts.set(labelOf(choiceField, item), (counts.get(labelOf(choiceField, item)) ?? 0) + 1)
    }
    const out = [...counts.entries()].sort((a, b) => b[1] - a[1]).slice(0, 10).map(([label, count]) => ({ label, count, share: answered ? Math.round((count / answered) * 100) : 0 }))
    if (!out.length) notes.push({ code: 'no_answers' })
    return { kind: 'top', value: answered, field: { key: choiceField.key, label: choiceField.label }, rows: out, filters, period: period ? { from: isoDay(period.from), to: isoDay(period.to) } : null, notes }
  }
  if (wantsTop && !choiceField) notes.push({ code: 'no_field' })
  return { kind: 'count', value: filtered.length, field: null, rows: [], filters, period: period ? { from: isoDay(period.from), to: isoDay(period.to) } : null, notes }
}

/** One response in a few lines: who and the answers that say most. */
export function summarise(form: StoredForm, entry: IndexedResponse, mask: (text: string) => string): { points: { label: string; value: string }[]; sentiment: keyof AiSentiment | null; themes: AiTheme[] } {
  const schema = responseSchema(form)
  const fields = schema ? allFields(schema).filter(field => isInputField(field.type) && !['hidden', 'calculated', 'signature', 'consent', 'file_upload', 'image_upload'].includes(field.type)) : []
  const data = answersOf(form, entry)
  const rank = (field: FormField) => (RATING.has(field.type) ? 0 : CHOICE.has(field.type) ? 1 : ['number', 'currency', 'date', 'datetime'].includes(field.type) ? 2 : field.type === 'long_text' ? 3 : 4)
  const points = fields
    // Who they are stays in the response itself, not in the summary
    .filter(field => data[field.key] != null && data[field.key] !== '' && !['full_name', 'email', 'phone', 'address'].includes(field.type) && !(field.type === 'short_text' && /\b(name|email|phone|address)\b/i.test(field.label)))
    .sort((a, b) => rank(a) - rank(b))
    .slice(0, 6)
    .map(field => {
      const value = data[field.key]
      const text = RATING.has(field.type) ? `${value} / ${maxOf(field)}` : Array.isArray(value) ? value.map(item => labelOf(field, item)).join(', ') : typeof value === 'object' ? Object.values(value as Record<string, unknown>).filter(Boolean).join(', ') : field.type === 'long_text' ? String(value).split(/(?<=[.!?])\s/)[0]! : labelOf(field, value)
      return { label: field.label, value: mask(text) }
    })
  const texts = textOf(fields, data)
  const all = texts.join(' ')
  return { points, sentiment: texts.length ? sentimentOf(all) : null, themes: texts.length ? themesOf(all).filter(key => key !== 'other') : [] }
}

/**
 * Mock form analytics (F18, docs/API-CONTRACT.md → Analytics).
 *
 *   GET /analytics/overview?from&to&form     totals with the period before, per day, channels
 *   GET /analytics/forms?from&to&q&sort&page one row per form (views … drop-off, sparkline)
 *   GET /analytics/forms/:id/funnel?from&to  pages and questions: reached, answered, left
 *
 * Completions, their days, channels and times come from the response data (decision 100), so the
 * numbers agree with Responses. Views, starts and where people stop are estimates that stay the
 * same per form and day (the real backend counts them from the fill-in page's events).
 */
import { inScope } from '../data/organisationStore'
import type { AnalyticsDay, AnalyticsOverview, AnalyticsTotals, FormAnalyticsRow, FormFunnel, FunnelField, FunnelPage } from '#shared/types/analytics'
import { requireAuth } from '../core/auth'
import { MockError, ok, paginate } from '../core/respond'
import { defineMockRoute } from '../core/route'
import { formResponses, responseSchema, type IndexedResponse } from '../data/responseData'
import { canSee, requireLevel } from '../data/formPermissions'
import { formsOf, type StoredForm } from '../data/formStore'
import type { MockTenant, MockUser } from '../data/tenants'

const DAY = 86_400_000
const DISPLAY_ONLY = new Set(['section', 'paragraph', 'divider', 'image', 'html', 'spacer'])
/** How much a question type makes people stop, and how long it takes (seconds). */
const WEIGHT: Record<string, number> = { long_text: 2.2, file: 2.8, signature: 2.1, address: 1.8, phone: 1.4, email: 1.3, matrix: 1.9, ranking: 1.6 }
const SECONDS: Record<string, number> = { long_text: 38, file: 24, signature: 14, address: 22, matrix: 26, ranking: 18, short_text: 7, email: 8, phone: 9, full_name: 9, number: 5, date: 6 }

function seeded(text: string) {
  let h = 2166136261
  for (const char of text) h = Math.imul(h ^ char.charCodeAt(0), 16777619)
  return () => {
    h = Math.imul(h ^ (h >>> 15), 2246822507)
    h = Math.imul(h ^ (h >>> 13), 3266489909)
    return ((h ^= h >>> 16) >>> 0) / 4294967296
  }
}

interface Period { from: number; to: number; days: number }
/** `from` and `to` as dates (default: the last 30 days, at most a year). */
function periodOf(query: Record<string, unknown>): Period {
  const today = Date.parse(new Date().toISOString().slice(0, 10))
  const parse = (value: unknown) => (typeof value === 'string' && /^\d{4}-\d{2}-\d{2}$/.test(value) ? Date.parse(value) : NaN)
  let to = parse(query.to)
  let from = parse(query.from)
  if (Number.isNaN(to) || to > today) to = today
  if (Number.isNaN(from) || from > to) from = to - 29 * DAY
  from = Math.max(from, to - 365 * DAY)
  return { from, to, days: Math.round((to - from) / DAY) + 1 }
}
const before = (period: Period): Period => ({ from: period.from - period.days * DAY, to: period.from - DAY, days: period.days })
const iso = (time: number) => new Date(time).toISOString().slice(0, 10)

/** One form's days in a period: completions from its responses, starts and views around them. */
function daysOf(form: StoredForm, entries: IndexedResponse[], period: Period): { daily: AnalyticsDay[]; within: IndexedResponse[] } {
  const rate = Math.min(0.95, Math.max(0.2, (form.completion_rate || 68) / 100))
  const daily = Array.from({ length: period.days }, (_, i) => ({ date: iso(period.from + i * DAY), views: 0, starts: 0, completions: 0 }))
  const within: IndexedResponse[] = []
  for (const entry of entries) {
    const index = Math.floor((entry.at - period.from) / DAY)
    if (index < 0 || index >= period.days) continue
    daily[index]!.completions++
    within.push(entry)
  }
  const open = form.status === 'published'
  for (const day of daily) {
    const random = seeded(`${form.id}:${day.date}`)
    const wandering = open ? Math.floor(random() * 3) : 0
    day.starts = day.completions ? Math.max(day.completions, Math.round((day.completions / rate) * (0.85 + random() * 0.3))) : wandering
    day.views = day.starts ? Math.round(day.starts * (1.3 + random() * 0.8)) : open ? Math.floor(random() * 4) : 0
  }
  return { daily, within }
}

const median = (entries: IndexedResponse[]) => {
  const times = entries.map(entry => entry.duration_seconds).filter((n): n is number => n != null).sort((a, b) => a - b)
  if (!times.length) return null
  const mid = Math.floor(times.length / 2)
  return Math.round(times.length % 2 ? times[mid]! : (times[mid - 1]! + times[mid]!) / 2)
}
function totalsOf(daily: AnalyticsDay[], within: IndexedResponse[]): AnalyticsTotals {
  const views = daily.reduce((sum, day) => sum + day.views, 0)
  const starts = daily.reduce((sum, day) => sum + day.starts, 0)
  const completions = daily.reduce((sum, day) => sum + day.completions, 0)
  return { views, starts, completions, completion_rate: starts ? Math.round((completions / starts) * 1000) / 10 : 0, median_seconds: median(within) }
}

const visibleForms = (tenant: MockTenant, user: MockUser) => formsOf(tenant).forms.filter(form => !form.deleted_at && inScope(tenant, form) && canSee(form, user))

/** Where people stop: the form's starters walk its questions in order; leavers spread by how hard each question is. */
function funnelOf(form: StoredForm, totals: AnalyticsTotals): { pages: FunnelPage[]; fields: FunnelField[] } {
  const schema = responseSchema(form)
  if (!schema) return { pages: [], fields: [] }
  const questions = schema.pages.flatMap((page, pageIndex) => page.rows.flatMap(row => row.fields).filter(field => !DISPLAY_ONLY.has(field.type)).map(field => ({ field, page: pageIndex })))
  const random = seeded(`${form.id}:funnel`)
  const weights = questions.map(({ field }, i) => (0.35 + random()) * (WEIGHT[field.type] ?? 1) * (field.required ? 1.3 : 0.6) * (i === 0 ? 1.6 : 1))
  const sum = weights.reduce((total, weight) => total + weight, 0) || 1
  const leavers = Math.max(0, totals.starts - totals.completions)
  let reached = totals.starts
  let given = 0
  const fields: FunnelField[] = questions.map(({ field, page }, i) => {
    const left = i === questions.length - 1 ? leavers - given : Math.min(reached, Math.round((leavers * weights[i]!) / sum))
    given += left
    const stayed = reached - left
    const row: FunnelField = {
      key: field.key,
      label: field.label,
      type: field.type,
      page,
      required: !!field.required,
      reached,
      answered: field.required ? stayed : Math.round(stayed * (0.55 + random() * 0.35)),
      left,
      seconds: Math.round((SECONDS[field.type] ?? 5) * (0.7 + random() * 0.6)),
    }
    reached = stayed
    return row
  })
  let carried = totals.starts
  const pages: FunnelPage[] = schema.pages.map((page, index) => {
    const own = fields.filter(item => item.page === index)
    const first = own[0]?.reached ?? carried
    const left = own.reduce((total, item) => total + item.left, 0)
    carried = first - left
    return { index, title: page.title || null, reached: first, left }
  })
  return { pages, fields }
}

export const analyticsOverview = defineMockRoute(({ event, query }) => {
  const { tenant, user } = requireAuth(event)
  const period = periodOf(query)
  let forms = visibleForms(tenant, user)
  if (typeof query.form === 'string' && query.form) {
    const form = forms.find(item => item.id === query.form)
    if (!form) throw new MockError('FRM-GEN-1004')
    requireLevel(form, user, 'responses')
    forms = [form]
  }
  const sumDays = (target: Period) => {
    const daily = Array.from({ length: target.days }, (_, i) => ({ date: iso(target.from + i * DAY), views: 0, starts: 0, completions: 0 }))
    const within: IndexedResponse[] = []
    let active = 0
    for (const form of forms) {
      const result = daysOf(form, formResponses(tenant, form), target)
      result.daily.forEach((day, i) => {
        daily[i]!.views += day.views
        daily[i]!.starts += day.starts
        daily[i]!.completions += day.completions
      })
      within.push(...result.within)
      if (result.daily.some(day => day.views)) active++
    }
    return { daily, within, active }
  }
  const now = sumDays(period)
  const then = sumDays(before(period))
  const channels = { link: 0, embed: 0, api: 0 }
  for (const entry of now.within) channels[entry.channel]++
  const overview: AnalyticsOverview = {
    from: iso(period.from),
    to: iso(period.to),
    totals: totalsOf(now.daily, now.within),
    previous: totalsOf(then.daily, then.within),
    daily: now.daily,
    channels,
    active_forms: now.active,
  }
  return ok(overview)
})

export const analyticsForms = defineMockRoute(({ event, query }) => {
  const { tenant, user } = requireAuth(event)
  const period = periodOf(query)
  const rows: FormAnalyticsRow[] = []
  for (const form of visibleForms(tenant, user)) {
    const entries = formResponses(tenant, form)
    const now = daysOf(form, entries, period)
    const totals = totalsOf(now.daily, now.within)
    if (form.status === 'draft' && !totals.views) continue
    const then = daysOf(form, entries, before(period))
    const previous = then.daily.reduce((sum, day) => sum + day.completions, 0)
    const { pages, fields } = funnelOf(form, totals)
    const worst = fields.reduce<FunnelField | null>((top, field) => (!top || field.left > top.left ? field : top), null)
    rows.push({
      id: form.id,
      name: form.name,
      status: form.status,
      ...totals,
      change: previous ? Math.round(((totals.completions - previous) / previous) * 100) : null,
      trend: now.daily.map(day => day.completions),
      drop_off: worst && worst.left && totals.starts ? { page: worst.page, page_title: pages[worst.page]?.title ?? null, field: worst.key, field_label: worst.label, rate: Math.round((worst.left / totals.starts) * 1000) / 10 } : null,
    })
  }
  const sort = typeof query.sort === 'string' && query.sort ? query.sort : '-completions'
  const desc = sort.startsWith('-')
  const key = (desc ? sort.slice(1) : sort) as keyof FormAnalyticsRow
  rows.sort((a, b) => {
    const x = a[key]
    const y = b[key]
    const order = typeof x === 'number' && typeof y === 'number' ? x - y : x == null ? 1 : y == null ? -1 : String(x).localeCompare(String(y), undefined, { numeric: true })
    return desc ? -order : order
  })
  const { data, meta } = paginate(rows, { ...query, sort: undefined }, (row, q) => row.name.toLowerCase().includes(q))
  return ok(data, meta)
})

export const formFunnel = defineMockRoute(({ event, query }) => {
  const { tenant, user } = requireAuth(event)
  const form = visibleForms(tenant, user).find(item => item.id === getRouterParam(event, 'id'))
  if (!form) throw new MockError('FRM-GEN-1004')
  requireLevel(form, user, 'responses')
  const now = daysOf(form, formResponses(tenant, form), periodOf(query))
  const totals = totalsOf(now.daily, now.within)
  const funnel: FormFunnel = { form: { id: form.id, name: form.name, status: form.status }, totals, ...funnelOf(form, totals) }
  return ok(funnel)
})


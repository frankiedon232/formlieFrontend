/**
 * Mock form analytics (F18, docs/API-CONTRACT.md → Analytics).
 *
 *   GET /analytics/overview?from&to&form     totals with the period before, per day, channels
 *   GET /analytics/forms?from&to&q&sort&page one row per form (views … drop-off, sparkline)
 *   GET /analytics/forms/:id/funnel?from&to  pages and questions: reached, answered, left
 *
 * Completions, their days, channels and times come from the response data (decision 100), so the
 * numbers agree with Responses. Views, starts, the funnel and where people stop come from the
 * fill-in page's recorded events (owner decision 2026-10-15, data/fillEventStore.ts), counted by the
 * shared rules in shared/utils/analytics/events.ts. A form without events shows zeros.
 */
import type { AnalyticsDay, AnalyticsOverview, AnalyticsTotals, FormAnalyticsRow, FormFunnel, FunnelField, FunnelPage } from '#shared/types/analytics'
import { completionRate, visitCounts, visitFunnel, visitsPerDay, type FillEvent } from '#shared/utils/analytics/events'
import { funnelQuestions } from '#shared/utils/analytics/questions'
import { allFields } from '#shared/utils/forms/build'
import { dayOf } from '#shared/utils/dashboard/buckets'
import { requireAuth } from '../core/auth'
import { calendarOf } from './dashboard'
import { MockError, ok, paginate } from '../core/respond'
import { defineMockRoute } from '../core/route'
import { formResponses, responseSchema, type IndexedResponse } from '../data/responseData'
import { canSee, requireLevel } from '../data/formPermissions'
import { formFillEvents } from '../data/fillEventStore'
import { formsOf, type StoredForm } from '../data/formStore'
import type { MockTenant, MockUser } from '../data/tenants'

const DAY = 86_400_000

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

/** The form's events whose (UTC) day falls in the period. */
const eventsIn = (events: FillEvent[], period: Period) => {
  const first = iso(period.from)
  const last = iso(period.to)
  return events.filter(event => {
    const day = event.at.slice(0, 10)
    return day >= first && day <= last
  })
}

/** One form's days in a period: completions from its responses, views and starts from its events. */
interface Days {
  daily: AnalyticsDay[]
  within: IndexedResponse[]
  /** Distinct visits in the whole period (a visit across midnight counts once here). */
  visits: { views: number; starts: number }
  events: FillEvent[]
}
function daysOf(entries: IndexedResponse[], all: FillEvent[], period: Period, timeZone?: string): Days {
  const dates = Array.from({ length: period.days }, (_, i) => iso(period.from + i * DAY))
  const events = eventsIn(all, period)
  // Days are the workspace's (its time zone, owner 2026-10-15)
  const daily: AnalyticsDay[] = visitsPerDay(events, dates, timeZone).map(day => ({ ...day, completions: 0 }))
  const within: IndexedResponse[] = []
  for (const entry of entries) {
    const index = timeZone ? dates.indexOf(iso(dayOf(entry.at, timeZone))) : Math.floor((entry.at - period.from) / DAY)
    if (index < 0 || index >= period.days) continue
    daily[index]!.completions++
    within.push(entry)
  }
  return { daily, within, visits: visitCounts(events), events }
}

const median = (entries: IndexedResponse[]) => {
  const times = entries.map(entry => entry.duration_seconds).filter((n): n is number => n != null).sort((a, b) => a - b)
  if (!times.length) return null
  const mid = Math.floor(times.length / 2)
  return Math.round(times.length % 2 ? times[mid]! : (times[mid - 1]! + times[mid]!) / 2)
}
function totalsOf({ daily, within, visits }: Pick<Days, 'daily' | 'within' | 'visits'>): AnalyticsTotals {
  const completions = daily.reduce((sum, day) => sum + day.completions, 0)
  return { ...visits, completions, completion_rate: completionRate(completions, visits.starts), median_seconds: median(within) }
}

const visibleForms = (tenant: MockTenant, user: MockUser) => formsOf(tenant).forms.filter(form => !form.deleted_at && canSee(form, user))

/** Pages and questions from the period's events (shared/utils/analytics/events.ts → visitFunnel). */
function funnelOf(form: StoredForm, events: FillEvent[], submitted: ReadonlySet<string>): { pages: FunnelPage[]; fields: FunnelField[] } {
  const schema = responseSchema(form)
  if (!schema) return { pages: [], fields: [] }
  const byKey = new Map(allFields(schema).map(field => [field.key, field]))
  const funnel = visitFunnel(events, { pages: schema.pages.length, questions: funnelQuestions(schema), submitted })
  return {
    pages: funnel.pages.map(page => ({ ...page, title: schema.pages[page.index]?.title || null })),
    fields: funnel.fields.map(row => {
      const field = byKey.get(row.key)
      return { ...row, label: field?.label ?? row.key, type: field?.type ?? 'short_text', required: !!field?.required }
    }),
  }
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
  const sources = forms.map(form => ({ entries: formResponses(tenant, form), events: formFillEvents(tenant, form).events }))
  const sumDays = (target: Period) => {
    const daily = Array.from({ length: target.days }, (_, i) => ({ date: iso(target.from + i * DAY), views: 0, starts: 0, completions: 0 }))
    const within: IndexedResponse[] = []
    const visits = { views: 0, starts: 0 }
    let active = 0
    for (const source of sources) {
      const result = daysOf(source.entries, source.events, target, calendarOf(tenant).timeZone)
      result.daily.forEach((day, i) => {
        daily[i]!.views += day.views
        daily[i]!.starts += day.starts
        daily[i]!.completions += day.completions
      })
      within.push(...result.within)
      visits.views += result.visits.views
      visits.starts += result.visits.starts
      if (result.visits.views) active++
    }
    return { daily, within, visits, active }
  }
  const now = sumDays(period)
  const then = sumDays(before(period))
  const channels = { link: 0, embed: 0, api: 0 }
  for (const entry of now.within) channels[entry.channel]++
  const overview: AnalyticsOverview = {
    from: iso(period.from),
    to: iso(period.to),
    totals: totalsOf(now),
    previous: totalsOf(then),
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
    const { events, submitted } = formFillEvents(tenant, form)
    const now = daysOf(entries, events, period, calendarOf(tenant).timeZone)
    const totals = totalsOf(now)
    if (form.status === 'draft' && !totals.views) continue
    const then = daysOf(entries, events, before(period), calendarOf(tenant).timeZone)
    const previous = then.daily.reduce((sum, day) => sum + day.completions, 0)
    const { pages, fields } = funnelOf(form, now.events, submitted)
    const worst = fields.reduce<FunnelField | null>((top, field) => (!top || field.left > top.left ? field : top), null)
    rows.push({
      id: form.id,
      name: form.name,
      status: form.status,
      ...totals,
      change: previous ? Math.round(((totals.completions - previous) / previous) * 100) : null,
      trend: now.daily.map(day => day.completions),
      drop_off: worst && worst.left && totals.starts ? { page: worst.page, page_title: pages[worst.page]?.title ?? null, field: worst.key, field_label: worst.label, rate: completionRate(worst.left, totals.starts) } : null,
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
  const { events, submitted } = formFillEvents(tenant, form)
  const now = daysOf(formResponses(tenant, form), events, periodOf(query), calendarOf(tenant).timeZone)
  const funnel: FormFunnel = { form: { id: form.id, name: form.name, status: form.status }, totals: totalsOf(now), ...funnelOf(form, now.events, submitted) }
  return ok(funnel)
})

/**
 * Fill-in analytics from recorded events (owner decision 2026-10-15, docs/API-CONTRACT.md → Analytics).
 *
 * The public fill-in page (link and embed, never previews) records what happens during one visit:
 *   view    once per visit, when the form shows
 *   start   once, on the first input
 *   answer  { field } the first time each question gets a value
 *   page    { page } when a page is shown (multi-page forms; 0-based schema page index)
 * A visit is a random id kept in the tab's sessionStorage (no personal data, no IP). The same
 * visit + kind (+ field / page) twice counts once. The submit body carries the same id as
 * `session`, so the visits that finished are known.
 *
 * Counting rules (pure; the backend ports them with parity tests):
 *   views / starts      distinct visits with a view / start (per day: the event's day in the workspace's time zone)
 *   funnel per page     started visits that reached the page (page 0: every started visit);
 *                       left = started visits that never submitted whose furthest page it was
 *   drop-off per field  started visits that never submitted whose last answered question, in
 *                       form order, is this one
 *   no events           zeros everywhere
 */

import { dayOf } from '../dashboard/buckets'

export const FILL_EVENT_KINDS = ['view', 'start', 'answer', 'page'] as const
export type FillEventKind = (typeof FILL_EVENT_KINDS)[number]
export type FillChannel = 'link' | 'embed'

/** POST /public/forms/{key}/events body. */
export interface FillEventInput {
  session: string
  kind: FillEventKind
  field?: string
  page?: number
  channel: FillChannel
}

/** A recorded event (server side; `at` is an ISO time). */
export interface FillEvent {
  session: string
  kind: FillEventKind
  field: string | null
  page: number | null
  channel: FillChannel
  at: string
}

/** A visit id: random, 22 to 64 URL-safe characters. */
export const VISIT_ID_PATTERN = /^[A-Za-z0-9_-]{22,64}$/
export const isVisitId = (value: unknown): value is string => typeof value === 'string' && VISIT_ID_PATTERN.test(value)

/** A fresh visit id: 16 random bytes as base64url (22 characters). */
export function newVisitId(): string {
  const bytes = new Uint8Array(16)
  globalThis.crypto.getRandomValues(bytes)
  let text = ''
  for (const byte of bytes) text += String.fromCharCode(byte)
  return btoa(text).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '')
}

const FIELD_KEY = /^[A-Za-z0-9_.-]{1,100}$/

/**
 * A checked event, or null when it can't be one: a bad visit id or kind, an answer without a field
 * key, a page without a whole page number (0 to 999). View and start never carry a field or page.
 */
export function normaliseFillEvent(input: {
  session?: unknown
  kind?: unknown
  field?: unknown
  page?: unknown
  channel?: unknown
}): Omit<FillEvent, 'at'> | null {
  if (!isVisitId(input.session)) return null
  if (!FILL_EVENT_KINDS.includes(input.kind as FillEventKind)) return null
  const kind = input.kind as FillEventKind
  const channel: FillChannel = input.channel === 'embed' ? 'embed' : 'link'
  if (kind === 'answer') {
    if (typeof input.field !== 'string' || !FIELD_KEY.test(input.field)) return null
    return { session: input.session, kind, field: input.field, page: null, channel }
  }
  if (kind === 'page') {
    if (typeof input.page !== 'number' || !Number.isInteger(input.page) || input.page < 0 || input.page > 999) return null
    return { session: input.session, kind, field: null, page: input.page, channel }
  }
  return { session: input.session, kind, field: null, page: null, channel }
}

/** What makes two events the same: visit + kind (+ field for answers, + page for pages). */
export function fillEventKey(event: { session: string; kind: FillEventKind; field?: string | null; page?: number | null }): string {
  const extra = event.kind === 'answer' ? (event.field ?? '') : event.kind === 'page' ? String(event.page ?? '') : ''
  return `${event.session}|${event.kind}|${extra}`
}

/** Repeats left out (the first one counts). */
export function dedupeFillEvents<T extends { session: string; kind: FillEventKind; field?: string | null; page?: number | null }>(events: readonly T[]): T[] {
  const seen = new Set<string>()
  return events.filter(event => {
    const key = fillEventKey(event)
    if (seen.has(key)) return false
    seen.add(key)
    return true
  })
}

/** The event's day: in the workspace's time zone when given (owner 2026-10-15, days are the workspace's), else UTC. */
const dayOfEvent = (event: FillEvent, timeZone?: string) => (timeZone ? new Date(dayOf(Date.parse(event.at), timeZone)).toISOString().slice(0, 10) : event.at.slice(0, 10))

/** Distinct visits with a view and with a start. */
export function visitCounts(events: readonly FillEvent[]): { views: number; starts: number } {
  const views = new Set<string>()
  const starts = new Set<string>()
  for (const event of events) {
    if (event.kind === 'view') views.add(event.session)
    else if (event.kind === 'start') starts.add(event.session)
  }
  return { views: views.size, starts: starts.size }
}

/** Views and starts per day (`dates` as YYYY-MM-DD, UTC): distinct visits with a view / start that day. */
export function visitsPerDay(events: readonly FillEvent[], dates: readonly string[], timeZone?: string): { date: string; views: number; starts: number }[] {
  const views = new Map<string, Set<string>>()
  const starts = new Map<string, Set<string>>()
  for (const event of events) {
    const target = event.kind === 'view' ? views : event.kind === 'start' ? starts : null
    if (!target) continue
    const day = dayOfEvent(event, timeZone)
    let set = target.get(day)
    if (!set) target.set(day, (set = new Set()))
    set.add(event.session)
  }
  return dates.map(date => ({ date, views: views.get(date)?.size ?? 0, starts: starts.get(date)?.size ?? 0 }))
}

/** A question in form order: its key and its page (0-based schema page index). */
export interface FunnelQuestionRef {
  key: string
  page: number
}

export interface VisitFunnel {
  pages: { index: number; reached: number; left: number }[]
  fields: { key: string; page: number; reached: number; answered: number; left: number; seconds: number }[]
}

interface Visit {
  started: boolean
  pages: Set<number>
  answered: Set<string>
  events: FillEvent[]
}

function visitsOf(events: readonly FillEvent[]): Map<string, Visit> {
  const visits = new Map<string, Visit>()
  for (const event of events) {
    let visit = visits.get(event.session)
    if (!visit) visits.set(event.session, (visit = { started: false, pages: new Set(), answered: new Set(), events: [] }))
    visit.events.push(event)
    if (event.kind === 'start') visit.started = true
    else if (event.kind === 'page' && event.page != null) visit.pages.add(event.page)
    else if (event.kind === 'answer' && event.field) visit.answered.add(event.field)
  }
  return visits
}

/** The last answered question in form order (null: none answered). */
export function lastAnswered(answered: ReadonlySet<string>, questions: readonly FunnelQuestionRef[]): string | null {
  for (let i = questions.length - 1; i >= 0; i--) if (answered.has(questions[i]!.key)) return questions[i]!.key
  return null
}

/** For each visit that started and never submitted: the question it stopped after (key → visits). */
export function dropOffCounts(events: readonly FillEvent[], questions: readonly FunnelQuestionRef[], submitted: ReadonlySet<string>): Map<string, number> {
  const counts = new Map<string, number>()
  for (const [session, visit] of visitsOf(events)) {
    if (!visit.started || submitted.has(session)) continue
    const key = lastAnswered(visit.answered, questions)
    if (key) counts.set(key, (counts.get(key) ?? 0) + 1)
  }
  return counts
}

const medianOf = (values: number[]) => {
  if (!values.length) return 0
  const sorted = [...values].sort((a, b) => a - b)
  const mid = Math.floor(sorted.length / 2)
  return Math.round(sorted.length % 2 ? sorted[mid]! : (sorted[mid - 1]! + sorted[mid]!) / 2)
}

/**
 * Pages and questions of a form from its events.
 *   page reached   started visits that showed the page (page 0: every started visit)
 *   page left      started, never submitted, and this was the furthest page shown
 *   field reached  started visits that reached its page or answered it
 *   field answered started visits that answered it
 *   field left     started, never submitted, and it was the last answered question in form order
 *   field seconds  median seconds from the visit's previous view / page / answer event to this answer (0: none)
 */
export function visitFunnel(
  events: readonly FillEvent[],
  { pages, questions, submitted }: { pages: number; questions: readonly FunnelQuestionRef[]; submitted: ReadonlySet<string> },
): VisitFunnel {
  const started = [...visitsOf(events)].filter(([, visit]) => visit.started)
  const reached = (visit: Visit, page: number) => page === 0 || visit.pages.has(page)
  const pageRows = Array.from({ length: pages }, (_, index) => ({ index, reached: 0, left: 0 }))
  const fieldStats = new Map(questions.map(question => [question.key, { reached: 0, answered: 0, left: 0, times: [] as number[] }]))
  for (const [session, visit] of started) {
    for (const row of pageRows) if (reached(visit, row.index)) row.reached++
    const unfinished = !submitted.has(session)
    if (unfinished && pageRows.length) {
      const furthest = Math.min(pageRows.length - 1, Math.max(0, ...visit.pages))
      pageRows[furthest]!.left++
    }
    const last = unfinished ? lastAnswered(visit.answered, questions) : null
    for (const question of questions) {
      const stats = fieldStats.get(question.key)!
      const answered = visit.answered.has(question.key)
      if (answered || reached(visit, question.page)) stats.reached++
      if (answered) stats.answered++
      if (last === question.key) stats.left++
    }
    // Time on each question: from the event before its answer (the start comes with the first input, so it doesn't count)
    const timeline = visit.events.filter(event => event.kind !== 'start').sort((a, b) => Date.parse(a.at) - Date.parse(b.at))
    timeline.forEach((event, i) => {
      if (event.kind !== 'answer' || !event.field || i === 0) return
      const stats = fieldStats.get(event.field)
      if (stats) stats.times.push(Math.max(0, (Date.parse(event.at) - Date.parse(timeline[i - 1]!.at)) / 1000))
    })
  }
  return {
    pages: pageRows,
    fields: questions.map(question => {
      const { reached, answered, left, times } = fieldStats.get(question.key)!
      return { key: question.key, page: question.page, reached, answered, left, seconds: medianOf(times) }
    }),
  }
}

/** Completions of starts, 0 to 100 with one decimal (0 without starts; never above 100). */
export const completionRate = (completions: number, starts: number) => (starts ? Math.min(100, Math.round((completions / starts) * 1000) / 10) : 0)

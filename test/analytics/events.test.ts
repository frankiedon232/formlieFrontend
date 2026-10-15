import { describe, expect, it } from 'vitest'
import {
  completionRate,
  dedupeFillEvents,
  dropOffCounts,
  fillEventKey,
  isVisitId,
  lastAnswered,
  newVisitId,
  normaliseFillEvent,
  visitCounts,
  visitFunnel,
  visitsPerDay,
  type FillEvent,
} from '../../shared/utils/analytics/events'
import { funnelQuestions } from '../../shared/utils/analytics/questions'
import type { FormSchemaV1 } from '../../shared/utils/forms/schema'

const A = 'visitAAAAAAAAAAAAAAAAAAA'
const B = 'visitBBBBBBBBBBBBBBBBBBB'
const C = 'visitCCCCCCCCCCCCCCCCCCC'
const D = 'visitDDDDDDDDDDDDDDDDDDD'

const ev = (session: string, kind: FillEvent['kind'], at: string, extra: { field?: string; page?: number } = {}): FillEvent => ({
  session,
  kind,
  field: extra.field ?? null,
  page: extra.page ?? null,
  channel: 'link',
  at,
})

describe('visit ids', () => {
  it('makes 22 URL-safe characters, different each time', () => {
    const ids = new Set(Array.from({ length: 50 }, newVisitId))
    expect(ids.size).toBe(50)
    for (const id of ids) {
      expect(id).toMatch(/^[A-Za-z0-9_-]{22}$/)
      expect(isVisitId(id)).toBe(true)
    }
  })
  it('accepts 22 to 64 URL-safe characters only', () => {
    expect(isVisitId('a'.repeat(22))).toBe(true)
    expect(isVisitId('a'.repeat(64))).toBe(true)
    expect(isVisitId('a'.repeat(21))).toBe(false)
    expect(isVisitId('a'.repeat(65))).toBe(false)
    expect(isVisitId(`${'a'.repeat(22)}+`)).toBe(false)
    expect(isVisitId('a b'.repeat(10))).toBe(false)
    expect(isVisitId(undefined)).toBe(false)
    expect(isVisitId(12345)).toBe(false)
  })
})

describe('normaliseFillEvent', () => {
  it('keeps view and start without field or page', () => {
    expect(normaliseFillEvent({ session: A, kind: 'view', field: 'x', page: 2, channel: 'embed' })).toEqual({ session: A, kind: 'view', field: null, page: null, channel: 'embed' })
    expect(normaliseFillEvent({ session: A, kind: 'start' })).toEqual({ session: A, kind: 'start', field: null, page: null, channel: 'link' })
  })
  it('needs a field for answers and a whole page number for pages', () => {
    expect(normaliseFillEvent({ session: A, kind: 'answer' })).toBeNull()
    expect(normaliseFillEvent({ session: A, kind: 'answer', field: 'email' })?.field).toBe('email')
    expect(normaliseFillEvent({ session: A, kind: 'page', page: 1.5 })).toBeNull()
    expect(normaliseFillEvent({ session: A, kind: 'page', page: -1 })).toBeNull()
    expect(normaliseFillEvent({ session: A, kind: 'page', page: 2 })?.page).toBe(2)
  })
  it('refuses a bad visit id or kind', () => {
    expect(normaliseFillEvent({ session: 'short', kind: 'view' })).toBeNull()
    expect(normaliseFillEvent({ session: A, kind: 'submit' })).toBeNull()
  })
})

describe('dedupe', () => {
  it('counts the same visit + kind (+ field / page) once, the first one', () => {
    const events = [
      ev(A, 'view', '2026-10-01T10:00:00Z'),
      ev(A, 'view', '2026-10-01T10:05:00Z'),
      ev(A, 'answer', '2026-10-01T10:01:00Z', { field: 'name' }),
      ev(A, 'answer', '2026-10-01T10:02:00Z', { field: 'name' }),
      ev(A, 'answer', '2026-10-01T10:03:00Z', { field: 'email' }),
      ev(A, 'page', '2026-10-01T10:04:00Z', { page: 1 }),
      ev(A, 'page', '2026-10-01T10:06:00Z', { page: 1 }),
      ev(B, 'view', '2026-10-01T10:00:00Z'),
    ]
    const kept = dedupeFillEvents(events)
    expect(kept).toHaveLength(5)
    expect(kept[0]!.at).toBe('2026-10-01T10:00:00Z')
    expect(fillEventKey(events[0]!)).toBe(fillEventKey(events[1]!))
    expect(fillEventKey(events[2]!)).not.toBe(fillEventKey(events[4]!))
  })
})

describe('views and starts', () => {
  const events = [
    ev(A, 'view', '2026-10-01T09:00:00Z'),
    ev(A, 'start', '2026-10-01T09:01:00Z'),
    ev(A, 'view', '2026-10-01T09:30:00Z'), // a repeat that slipped through still counts once
    ev(B, 'view', '2026-10-01T23:59:00Z'),
    ev(B, 'start', '2026-10-02T00:01:00Z'), // started after midnight
    ev(C, 'view', '2026-10-02T12:00:00Z'),
  ]
  it('are distinct visits per day', () => {
    expect(visitsPerDay(events, ['2026-10-01', '2026-10-02', '2026-10-03'])).toEqual([
      { date: '2026-10-01', views: 2, starts: 1 },
      { date: '2026-10-02', views: 1, starts: 1 },
      { date: '2026-10-03', views: 0, starts: 0 },
    ])
  })
  it('are distinct visits in total', () => {
    expect(visitCounts(events)).toEqual({ views: 3, starts: 2 })
  })
})

describe('funnel and drop-off', () => {
  // Page 0: name, email · page 1: phone, notes
  const questions = [
    { key: 'name', page: 0 },
    { key: 'email', page: 0 },
    { key: 'phone', page: 1 },
    { key: 'notes', page: 1 },
  ]
  const events = [
    // A: finished, both pages
    ev(A, 'view', '2026-10-01T10:00:00Z'),
    ev(A, 'page', '2026-10-01T10:00:00Z', { page: 0 }),
    ev(A, 'start', '2026-10-01T10:00:10Z'),
    ev(A, 'answer', '2026-10-01T10:00:10Z', { field: 'name' }),
    ev(A, 'answer', '2026-10-01T10:00:30Z', { field: 'email' }),
    ev(A, 'page', '2026-10-01T10:00:40Z', { page: 1 }),
    ev(A, 'answer', '2026-10-01T10:01:00Z', { field: 'phone' }),
    // B: stopped on page 1 after the phone, but answered notes first (form order decides)
    ev(B, 'view', '2026-10-01T11:00:00Z'),
    ev(B, 'start', '2026-10-01T11:00:05Z'),
    ev(B, 'answer', '2026-10-01T11:00:05Z', { field: 'name' }),
    ev(B, 'page', '2026-10-01T11:00:20Z', { page: 1 }),
    ev(B, 'answer', '2026-10-01T11:00:40Z', { field: 'notes' }),
    ev(B, 'answer', '2026-10-01T11:01:00Z', { field: 'phone' }),
    // C: stopped on page 0 after the name
    ev(C, 'view', '2026-10-01T12:00:00Z'),
    ev(C, 'start', '2026-10-01T12:00:05Z'),
    ev(C, 'answer', '2026-10-01T12:00:05Z', { field: 'name' }),
    // D: only looked
    ev(D, 'view', '2026-10-01T13:00:00Z'),
  ]
  const submitted = new Set([A])

  it('takes the last answered question in form order', () => {
    expect(lastAnswered(new Set(['notes', 'phone']), questions)).toBe('notes')
    expect(lastAnswered(new Set(['email', 'name']), questions)).toBe('email')
    expect(lastAnswered(new Set(), questions)).toBeNull()
  })

  it('counts drop-off only for started visits that never submitted', () => {
    expect(Object.fromEntries(dropOffCounts(events, questions, submitted))).toEqual({ notes: 1, name: 1 })
    // Once B submits, only C is left
    expect(Object.fromEntries(dropOffCounts(events, questions, new Set([A, B])))).toEqual({ name: 1 })
  })

  it('counts started visits reaching each page and where they left', () => {
    const funnel = visitFunnel(events, { pages: 2, questions, submitted })
    expect(funnel.pages).toEqual([
      { index: 0, reached: 3, left: 1 },
      { index: 1, reached: 2, left: 1 },
    ])
    const byKey = Object.fromEntries(funnel.fields.map(field => [field.key, field]))
    expect(byKey.name).toMatchObject({ reached: 3, answered: 3, left: 1 })
    expect(byKey.email).toMatchObject({ reached: 3, answered: 1, left: 0 })
    expect(byKey.phone).toMatchObject({ reached: 2, answered: 2, left: 0 })
    expect(byKey.notes).toMatchObject({ reached: 2, answered: 1, left: 1 })
    // Seconds: from the event before the answer (email: 20 s after the name; phone: 20 s after page 1 (A), 20 s after notes (B))
    expect(byKey.email!.seconds).toBe(20)
    expect(byKey.phone!.seconds).toBe(20)
  })

  it('shows zeros without events', () => {
    expect(visitCounts([])).toEqual({ views: 0, starts: 0 })
    expect(visitsPerDay([], ['2026-10-01'])).toEqual([{ date: '2026-10-01', views: 0, starts: 0 }])
    const funnel = visitFunnel([], { pages: 2, questions, submitted: new Set() })
    expect(funnel.pages.every(page => page.reached === 0 && page.left === 0)).toBe(true)
    expect(funnel.fields.every(field => !field.reached && !field.answered && !field.left && !field.seconds)).toBe(true)
    expect(dropOffCounts([], questions, new Set()).size).toBe(0)
    expect(completionRate(0, 0)).toBe(0)
  })

  it('keeps the completion rate between 0 and 100', () => {
    expect(completionRate(1, 3)).toBe(33.3)
    expect(completionRate(5, 3)).toBe(100)
  })
})

describe('funnelQuestions', () => {
  it('lists answerable questions in form order with their page, leaving out display, hidden and calculated fields', () => {
    const field = (key: string, type: string) => ({ id: key, key, type, label: key })
    const schema = {
      pages: [
        { id: 'p1', title: '', rows: [{ id: 'r1', fields: [field('intro', 'paragraph'), field('name', 'short_text')] }, { id: 'r2', fields: [field('ref', 'hidden'), field('total', 'calculated')] }] },
        { id: 'p2', title: '', rows: [{ id: 'r3', fields: [field('email', 'email'), field('line', 'divider')] }] },
      ],
    } as unknown as FormSchemaV1
    expect(funnelQuestions(schema)).toEqual([
      { key: 'name', page: 0 },
      { key: 'email', page: 1 },
    ])
  })
})

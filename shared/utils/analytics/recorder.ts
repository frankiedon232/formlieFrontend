/**
 * The fill-in page's event recorder (see events.ts for what each event means). Each event goes out
 * once per visit: view once, start once (a start implies the view), one answer per question (an
 * answer implies the start), one page event per page. Pure: `send` does the network part.
 */
import { fillEventKey, type FillChannel, type FillEventInput } from './events'

export interface FillRecorder {
  readonly session: string
  view: () => void
  start: () => void
  page: (index: number) => void
  answer: (field: string) => void
}

export function createFillRecorder(session: string, channel: FillChannel, send: (event: FillEventInput) => void): FillRecorder {
  const sent = new Set<string>()
  const once = (event: FillEventInput) => {
    const key = fillEventKey(event)
    if (sent.has(key)) return
    sent.add(key)
    send(event)
  }
  const view = () => once({ session, kind: 'view', channel })
  const start = () => {
    view()
    once({ session, kind: 'start', channel })
  }
  return {
    session,
    view,
    start,
    page: index => {
      if (Number.isInteger(index) && index >= 0) once({ session, kind: 'page', page: index, channel })
    },
    answer: field => {
      if (!field) return
      start()
      once({ session, kind: 'answer', field, channel })
    },
  }
}

/** A question has a value: text with something in it, a list with an item, an object with a filled part, any number or true. */
export function hasAnswer(value: unknown): boolean {
  if (value == null || value === false) return false
  if (typeof value === 'string') return value.trim().length > 0
  if (Array.isArray(value)) return value.some(hasAnswer)
  if (typeof value === 'object') return Object.values(value as Record<string, unknown>).some(hasAnswer)
  return true
}

/**
 * The questions (`keys`) that have a value now and a different one than when the form opened
 * (`baseline`: defaults, link prefill, restored drafts), so starting values never count as answers.
 */
export function answeredSince(values: Record<string, unknown>, baseline: Record<string, unknown>, keys: Iterable<string>): string[] {
  const out: string[] = []
  for (const key of keys) {
    if (!hasAnswer(values[key])) continue
    if (JSON.stringify(values[key] ?? null) === JSON.stringify(baseline[key] ?? null)) continue
    out.push(key)
  }
  return out
}

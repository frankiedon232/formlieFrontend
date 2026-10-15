/**
 * Fill-in events for the mock (analytics, owner decision 2026-10-15; rules in
 * shared/utils/analytics/events.ts). Two sources, read together:
 *   - recorded: what the public fill-in page sends (POST /public/forms/:key/events), repeats of the
 *     same visit + kind (+ field / page) ignored; persisted across dev reloads;
 *   - samples: for every sample response a finished visit (view, start, answers, pages), plus
 *     visits that stopped part way and visits that only looked, stable per form, so sample forms
 *     have analytics to show. A form without samples or recorded events shows zeros.
 * Finished visits: the samples' own, plus the `session` of every real response.
 */
import { fillEventKey, type FillEvent, type FunnelQuestionRef } from '#shared/utils/analytics/events'
import { funnelQuestions } from '#shared/utils/analytics/questions'
import { loadPersisted, savePersisted } from '../core/persist'
import { formResponses, responseSchema, type IndexedResponse } from './responseData'
import { responsesOf } from './responseStore'
import { rngOf } from './sampleAnswers'
import type { StoredForm } from './formStore'
import type { MockTenant } from './tenants'

const MAX_PER_FORM = 50_000
const DAY = 86_400_000

const recorded = new Map<string, FillEvent[]>(Object.entries(loadPersisted<Record<string, FillEvent[]>>('fill-events', {})))
const keys = new Map<string, Set<string>>()

function keysOf(formId: string): Set<string> {
  let set = keys.get(formId)
  if (!set) keys.set(formId, (set = new Set((recorded.get(formId) ?? []).map(fillEventKey))))
  return set
}

/** Store one event; false when the visit already sent it (a repeat is ignored). */
export function recordFillEvent(formId: string, event: FillEvent): boolean {
  const seen = keysOf(formId)
  const key = fillEventKey(event)
  if (seen.has(key)) return false
  seen.add(key)
  const list = recorded.get(formId) ?? []
  list.push(event)
  if (list.length > MAX_PER_FORM) list.splice(0, list.length - MAX_PER_FORM)
  recorded.set(formId, list)
  savePersisted('fill-events', () => Object.fromEntries(recorded))
  return true
}

// ── Samples ────────────────────────────────────────────────────────────────────────────
/** How much a question type makes people stop (abandoned sample visits). */
const HARD: Record<string, number> = { long_text: 2.2, file: 2.8, signature: 2.1, address: 1.8, phone: 1.4, email: 1.3, matrix: 1.9, ranking: 1.6 }

interface Samples {
  events: FillEvent[]
  done: Set<string>
}
const sampleCache = new WeakMap<IndexedResponse[], Samples>()

const at = (time: number) => new Date(time).toISOString()
const sessionFor = (seed: string) => `smp_${seed.replace(/[^A-Za-z0-9]/g, '').slice(-40).padStart(24, '0')}`

function sampleEvents(form: StoredForm, entries: IndexedResponse[]): Samples {
  const cached = sampleCache.get(entries)
  if (cached) return cached
  const out: Samples = { events: [], done: new Set() }
  const schema = responseSchema(form)
  const samples = entries.filter(entry => entry.source.kind === 'sample' && entry.channel !== 'api')
  if (!schema || !samples.length) return (sampleCache.set(entries, out), out)
  const questions = funnelQuestions(schema)
  const pageCount = schema.pages.length
  const required = new Map(schema.pages.flatMap(page => page.rows.flatMap(row => row.fields)).map(field => [field.key, !!field.required]))
  const types = new Map(schema.pages.flatMap(page => page.rows.flatMap(row => row.fields)).map(field => [field.key, field.type]))
  const push = (session: string, kind: FillEvent['kind'], time: number, channel: FillEvent['channel'], extra: { field?: string; page?: number } = {}) =>
    out.events.push({ session, kind, field: extra.field ?? null, page: extra.page ?? null, channel, at: at(time) })

  /** One visit: looked at `from`, then answered `asked` one after another until `until`. */
  const visit = (session: string, channel: FillEvent['channel'], from: number, until: number, asked: FunnelQuestionRef[], rng: () => number) => {
    push(session, 'view', from, channel)
    if (pageCount > 1) push(session, 'page', from, channel, { page: 0 })
    if (!asked.length) return
    const begin = from + (5 + rng() * 30) * 1000
    push(session, 'start', begin, channel)
    const step = Math.max(1000, (until - begin) / Math.max(1, asked.length))
    let page = 0
    asked.forEach((question, i) => {
      const time = begin + i * step + rng() * step * 0.5
      if (question.page > page) {
        for (let p = page + 1; p <= question.page; p++) push(session, 'page', time - 1000, channel, { page: p })
        page = question.page
      }
      push(session, 'answer', time, channel, { field: question.key })
    })
  }

  // Finished visits: one per sample response (optional questions skipped now and then)
  samples.forEach(entry => {
    const rng = rngOf(`${entry.id}:visit`)
    const session = sessionFor(entry.id)
    const seconds = entry.duration_seconds ?? 60
    const asked = questions.filter(question => required.get(question.key) || rng() < 0.75)
    visit(session, entry.channel === 'embed' ? 'embed' : 'link', entry.at - (seconds + 10 + rng() * 40) * 1000, entry.at - 1000, asked, rng)
    // Every page shown, also pages whose questions were all skipped
    for (let p = 1; p < pageCount; p++) if (!asked.some(question => question.page >= p)) push(session, 'page', entry.at - 2000, entry.channel === 'embed' ? 'embed' : 'link', { page: p })
    out.done.add(session)
  })

  // Visits that stopped part way (the form's completion rate) and visits that only looked
  const rng = rngOf(`${form.id}:visits`)
  const rate = Math.min(0.95, Math.max(0.2, (form.completion_rate || 68) / 100))
  const stopped = Math.round(samples.length * (1 / rate - 1))
  const weights = questions.map((question, i) => (0.35 + rng()) * (HARD[types.get(question.key) ?? ''] ?? 1) * (required.get(question.key) ? 1.3 : 0.6) * (i === 0 ? 1.6 : 1))
  const sum = weights.reduce((total, weight) => total + weight, 0) || 1
  const pick = () => {
    let target = rng() * sum
    for (let i = 0; i < weights.length; i++) if ((target -= weights[i]!) <= 0) return i
    return weights.length - 1
  }
  for (let n = 0; n < stopped + Math.round((samples.length + stopped) * (0.3 + rng() * 0.4)); n++) {
    const near = samples[Math.floor(rng() * samples.length)]!
    const from = near.at - rng() * DAY
    const session = sessionFor(`${form.id}${n}visit`)
    const channel = rng() < 0.16 ? 'embed' : 'link'
    if (n >= stopped || !questions.length) visit(session, channel, from, from, [], rng)
    else {
      const last = pick()
      visit(session, channel, from, from + (last + 1) * (8 + rng() * 20) * 1000, questions.slice(0, last + 1), rng)
    }
  }
  sampleCache.set(entries, out)
  return out
}

/** A form's events (samples and recorded) and the visits that submitted. */
export function formFillEvents(tenant: MockTenant, form: StoredForm): { events: FillEvent[]; submitted: Set<string> } {
  const samples = sampleEvents(form, formResponses(tenant, form))
  const own = recorded.get(form.id) ?? []
  const submitted = new Set(samples.done)
  for (const response of responsesOf(tenant).responses) if (response.form_id === form.id && response.session) submitted.add(response.session)
  return { events: own.length ? [...samples.events, ...own] : samples.events, submitted }
}

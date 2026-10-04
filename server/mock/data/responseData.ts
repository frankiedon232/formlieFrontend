/**
 * Every response of a form, in one place (F11, decision 100): seeded sample responses (so sample
 * forms have data to review and chart) plus the real ones sent through the public form, with the
 * team's review on top (status, tags, notes, edits, deletions). Lists, the inbox, insights, the
 * form overview, sidebar counts and form lists all read from here, so a new submission shows up
 * everywhere at once ("connect the dots", owner 2026-10-04).
 *
 * Samples: a form keeps `sample_count` (its seeded response count when first used) and
 * `sample_anchor` (when the samples end); sample i (0 = newest) has a stable id, time, person and
 * answers. Real responses come after the anchor and are numbered after the samples.
 */
import type { ResponseRespondent, ResponseStatus } from '#shared/types/responses'
import { allFields } from '#shared/utils/forms/build'
import { identityOf } from '#shared/utils/forms/identity'
import type { FormSchemaV1 } from '#shared/utils/forms/schema'
import { formLanguages } from '#shared/utils/forms/translations'
import { formsOf, saveForms, type StoredForm } from './formStore'
import { responsesOf, type StoredResponse } from './responseStore'
import { reviewOf, reviewVersion } from './responseReview'
import { parseSampleId, rngOf, sampleAnswers, sampleId, samplePerson, tailOf, type SamplePerson } from './sampleAnswers'
import type { MockTenant } from './tenants'
import { ensureSchema } from '../routes/formDraft'

export { parseSampleId, sampleId }

const DAY = 86_400_000

export interface IndexedResponse {
  id: string
  form_id: string
  number: number
  at: number
  status: ResponseStatus
  tags: string[]
  respondent: ResponseRespondent
  channel: 'link' | 'embed' | 'api'
  language: string
  duration_seconds: number | null
  notes_count: number
  edited: boolean
  possible_duplicate: { of: string; reason: string } | null
  form_version: number | null
  source: { kind: 'sample'; index: number; person: SamplePerson } | { kind: 'real'; stored: StoredResponse }
}

/** What respondents fill in (the published version; a draft's own schema before the first publish). */
export const responseSchema = (form: StoredForm): FormSchemaV1 | null => form.published_schema ?? form.schema ?? null

/** Sample count and anchor are fixed the first time a form's responses are read. */
function prepare(form: StoredForm, real: StoredResponse[]) {
  let changed = false
  if (form.sample_count == null) {
    form.sample_count = Math.max(0, form.responses_count - real.length)
    changed = true
  }
  if (!form.sample_anchor) {
    form.sample_anchor = new Date().toISOString()
    changed = true
  }
  return changed
}

/** When each sample came in, newest first: a steady rhythm (quieter weekends) that grows over time. */
function sampleTimes(form: StoredForm): number[] {
  const n = form.sample_count ?? 0
  if (!n) return []
  // Closed and archived forms stopped taking responses a while ago (their samples end earlier).
  const stopped = form.status === 'archived' ? 75 * DAY : form.status === 'closed' ? 21 * DAY : 0
  const end = Date.parse(form.sample_anchor!) - stopped
  const start = Math.min(Date.parse(form.created_at), end - DAY)
  const days = Math.max(1, Math.ceil((end - start) / DAY))
  const rng = rngOf(`${form.id}:days`)
  const weights = Array.from({ length: days }, (_, d) => {
    const weekday = new Date(start + d * DAY).getUTCDay()
    return (weekday === 0 || weekday === 6 ? 0.45 : 1) * (0.7 + 0.5 * ((d + 1) / days)) * (0.55 + rng())
  })
  const sum = weights.reduce((a, b) => a + b, 0)
  const exact = weights.map(w => (w / sum) * n)
  const counts = exact.map(Math.floor)
  let left = n - counts.reduce((a, b) => a + b, 0)
  exact.map((value, d) => [value - Math.floor(value), d] as const).sort((a, b) => b[0] - a[0]).forEach(([, d]) => left-- > 0 && counts[d]!++)
  const times: number[] = []
  for (let d = days - 1; d >= 0; d--) {
    const inDay = Array.from({ length: counts[d]! }, () => start + d * DAY + (7 + rng() * 14) * 3_600_000).sort((a, b) => b - a)
    for (const at of inDay) times.push(Math.min(at, end))
  }
  return times
}

const STATUS_RECENT: [ResponseStatus, number][] = [['new', 0.3], ['reviewed', 0.4], ['approved', 0.24], ['rejected', 0.06]]
const STATUS_OLD: [ResponseStatus, number][] = [['new', 0.02], ['reviewed', 0.33], ['approved', 0.52], ['rejected', 0.13]]
function sampleStatus(id: string, age: number): ResponseStatus {
  if (age < 1.5 * DAY) return 'new'
  const roll = rngOf(`${id}:status`)()
  let sum = 0
  for (const [status, share] of age < 14 * DAY ? STATUS_RECENT : STATUS_OLD) if (roll < (sum += share)) return status
  return 'reviewed'
}

/** Who sent it, as far as the form tells: its name and email questions. */
function respondentFrom(schema: FormSchemaV1 | null, data: Record<string, unknown>, known?: StoredResponse['respondent']): ResponseRespondent {
  if (known) return { name: known.name, email: known.email, kind: known.kind }
  if (!schema) return { name: null, email: null, kind: 'anonymous' }
  const fields = allFields(schema)
  const emailKey = identityOf(schema).email ?? fields.find(field => field.type === 'email')?.key
  const email = emailKey && typeof data[emailKey] === 'string' ? (data[emailKey] as string) : null
  const fullName = fields.find(field => field.type === 'full_name')
  const nameValue = fullName ? (data[fullName.key] as { first?: string; last?: string } | undefined) : undefined
  const first = fields.find(field => field.type === 'short_text' && /first|given/i.test(field.label ?? ''))
  const last = fields.find(field => field.type === 'short_text' && /last|family|surname/i.test(field.label ?? ''))
  const plain = fields.find(field => field.type === 'short_text' && /^\s*(your\s+)?(full\s+)?name\s*$/i.test(field.label ?? ''))
  const name =
    [nameValue?.first, nameValue?.last].filter(Boolean).join(' ') ||
    [first && data[first.key], last && data[last.key]].filter(value => typeof value === 'string' && value).join(' ') ||
    (plain && typeof data[plain.key] === 'string' ? (data[plain.key] as string) : '')
  return name || email ? { name: name || null, email, kind: 'answer' } : { name: null, email: null, kind: 'anonymous' }
}

const cache = new Map<string, { stamp: string; list: IndexedResponse[] }>()
/** Changes when the questions respondents fill in change (publish, or a sample form getting its questions). */
const schemaIds = new WeakMap<object, number>()
let nextSchemaId = 1
function schemaStamp(form: StoredForm) {
  const schema = responseSchema(form)
  if (!schema) return '0'
  let id = schemaIds.get(schema)
  if (!id) schemaIds.set(schema, (id = nextSchemaId++))
  return String(id)
}

/** A form's responses, newest first (deleted ones left out). Also keeps `responses_count` right. */
export function formResponses(tenant: MockTenant, form: StoredForm): IndexedResponse[] {
  const real = responsesOf(tenant).responses.filter(item => item.form_id === form.id)
  // Seeded sample forms get their questions the first time anyone opens them (here too).
  if (!form.schema) ensureSchema(form, tenant)
  if (prepare(form, real)) saveForms()
  const schema = responseSchema(form)
  const stamp = `${reviewVersion(form.id)}:${real.length}:${form.sample_count}:${form.sample_anchor}:${schemaStamp(form)}:${form.status}`
  const hit = cache.get(form.id)
  if (hit?.stamp === stamp) return hit.list

  const anchor = Date.parse(form.sample_anchor!)
  const languages = formLanguages(schema)
  const fields = schema ? allFields(schema).filter(field => field.type !== 'section' && field.type !== 'paragraph').length : 0
  const times = sampleTimes(form)
  const total = times.length
  const list: IndexedResponse[] = []
  /** Edited answers (F11 M2) count too, so a corrected name or email shows everywhere. */
  const sampleRespondent = (person: SamplePerson, edits?: Record<string, unknown>): ResponseRespondent => {
    if (!schema) return { name: null, email: null, kind: 'anonymous' }
    const data: Record<string, unknown> = {}
    for (const field of allFields(schema)) {
      if (field.type === 'email') data[field.key] = person.email
      if (field.type === 'full_name') data[field.key] = { first: person.first, last: person.last }
      if (field.type === 'short_text') {
        const label = field.label ?? ''
        if (/first|given/i.test(label)) data[field.key] = person.first
        else if (/last|family|surname/i.test(label)) data[field.key] = person.last
        else if (/name/i.test(label)) data[field.key] = `${person.first} ${person.last}`
      }
    }
    return respondentFrom(schema, { ...data, ...edits })
  }

  times.forEach((at, index) => {
    const id = sampleId(form.id, index)
    const review = reviewOf(id)
    if (review?.deleted_at) return
    const rng = rngOf(`${form.id}:meta:${index}`)
    const person = samplePerson(rngOf(`${form.id}:person:${index}`))
    list.push({
      id,
      form_id: form.id,
      number: total - index,
      at,
      status: review?.status ?? sampleStatus(id, anchor - at),
      tags: review?.tags ?? (rng() < 0.07 ? [['priority', 'follow-up', 'vip'][Math.floor(rng() * 3)]!] : []),
      respondent: sampleRespondent(person, review?.data),
      channel: rng() < 0.16 ? 'embed' : 'link',
      language: languages.length > 1 && rng() < 0.25 ? languages[1 + Math.floor(rng() * (languages.length - 1))]! : languages[0]!,
      duration_seconds: Math.round(Math.max(1, fields) * (9 + rng() * 14)),
      notes_count: review?.notes?.length ?? 0,
      edited: !!review?.data && Object.keys(review.data).length > 0,
      possible_duplicate: index > 0 && rng() < 0.012 && !review?.duplicate_cleared ? { of: sampleId(form.id, index - 1), reason: 'email_typo' } : null,
      form_version: form.versions?.length ? Math.max(1, (form.versions[0]?.number ?? 1) - (at < anchor - 60 * DAY ? 1 : 0)) : null,
      source: { kind: 'sample', index, person },
    })
  })

  // Real responses (newest first), numbered after the samples.
  const realSorted = [...real].sort((a, b) => Date.parse(a.submitted_at) - Date.parse(b.submitted_at))
  const realEntries = realSorted.map((stored, rank): IndexedResponse | null => {
    const review = reviewOf(stored.id)
    return review?.deleted_at
      ? null
      : {
          id: stored.id,
          form_id: form.id,
          number: total + rank + 1,
          at: Date.parse(stored.submitted_at),
          status: review?.status ?? 'new',
          tags: review?.tags ?? [],
          respondent: respondentFrom(schema, { ...stored.data, ...review?.data }, stored.respondent),
          channel: stored.channel,
          language: stored.language,
          duration_seconds: null,
          notes_count: review?.notes?.length ?? 0,
          edited: !!review?.data && Object.keys(review.data).length > 0,
          possible_duplicate: review?.duplicate_cleared ? null : (stored.possible_duplicate ?? null),
          form_version: stored.form_version,
          source: { kind: 'real', stored },
        }
  })
  const merged = [...realEntries.filter((item): item is IndexedResponse => !!item).reverse(), ...list].sort((a, b) => b.at - a.at)

  // The count everyone shows (lists, overview, limits) follows the responses that exist.
  if (form.responses_count !== merged.length) {
    form.responses_count = merged.length
    saveForms()
  }
  cache.set(form.id, { stamp, list: merged })
  return merged
}

const answerCache = new Map<string, Record<string, unknown>>()
/** Every answer of a response (the team's edits on top). */
export function answersOf(form: StoredForm, entry: IndexedResponse): Record<string, unknown> {
  const edits = reviewOf(entry.id)?.data
  if (entry.source.kind === 'real') return { ...entry.source.stored.data, ...edits }
  const key = `${entry.id}:${schemaStamp(form)}`
  let data = answerCache.get(key)
  if (!data) {
    const schema = responseSchema(form)
    data = schema ? sampleAnswers(schema, form.id, entry.source.index, entry.source.person, entry.at) : {}
    if (answerCache.size > 20_000) answerCache.clear()
    answerCache.set(key, data)
  }
  return edits ? { ...data, ...edits } : data
}

/** Find a response anywhere in the workspace. */
export function findResponse(tenant: MockTenant, id: string): { form: StoredForm; entry: IndexedResponse } | null {
  const forms = formsOf(tenant).forms
  const sample = parseSampleId(id)
  const stored = sample ? null : responsesOf(tenant).responses.find(item => item.id === id)
  const form = sample ? forms.find(item => tailOf(item.id) === sample.tail) : forms.find(item => item.id === stored?.form_id)
  if (!form) return null
  const entry = formResponses(tenant, form).find(item => item.id === id)
  return entry ? { form, entry } : null
}

/** Every response of every form this person may see (the inbox). */
export function workspaceResponses(tenant: MockTenant, visible: (form: StoredForm) => boolean): { form: StoredForm; entry: IndexedResponse }[] {
  return formsOf(tenant)
    .forms.filter(form => !form.deleted_at && visible(form))
    .flatMap(form => formResponses(tenant, form).map(entry => ({ form, entry })))
    .sort((a, b) => b.entry.at - a.entry.at)
}

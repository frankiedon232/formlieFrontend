/**
 * Responses (F11, docs/API-CONTRACT.md → Responses, decision 100). Reading needs at least
 * "Responses only" on the form (people access, decision 97); status, tags and notes too (reviewing
 * is the job of people given responses); changing answers and deleting need "Can edit".
 * Every change is recorded in the response's history and the audit trail.
 */
import { z } from 'zod'
import { RESPONSE_STATUSES, type ResponseDetail, type ResponseFormRow, type ResponseRow, type ResponseStatus } from '#shared/types/responses'
import { allFields } from '#shared/utils/forms/build'
import { isFileField } from '#shared/utils/forms/file-answers'
import { isInputField } from '#shared/utils/forms/fields'
import { requireAuth } from '../core/auth'
import { actorOf, recordAudit } from '../core/audit'
import { MockError, ok } from '../core/respond'
import { defineMockRoute } from '../core/route'
import { parseBody } from '../core/validate'
import { canSee, levelOf, requireLevel } from '../data/formPermissions'
import { formsOf, type StoredForm } from '../data/formStore'
import { answersOf, findResponse, formResponses, responseSchema, workspaceResponses, type IndexedResponse } from '../data/responseData'
import { insightsOf } from '../data/responseInsights'
import { reviewOf, updateReview } from '../data/responseReview'
import type { MockTenant, MockUser } from '../data/tenants'
import type { H3Event } from 'h3'

type Query = Record<string, unknown>
const DAY = 86_400_000
const list = (query: Query, key: string) => {
  const value = query[`filter[${key}]`]
  return typeof value === 'string' && value ? value.split(',') : null
}
const day = (value: unknown, end: boolean) => (typeof value === 'string' && value ? Date.parse(value) + (end ? DAY - 1 : 0) : null)

function formFor(tenant: MockTenant, user: MockUser, id: string | undefined): StoredForm {
  const form = formsOf(tenant).forms.find(item => item.id === id && !item.deleted_at)
  if (!form) throw new MockError('FRM-GEN-1004')
  requireLevel(form, user, 'responses')
  return form
}

/** Questions a respondent can answer (no headings, hidden or calculated fields). */
const questionsOf = (form: StoredForm) =>
  allFields(responseSchema(form) ?? { schema_version: 1, pages: [] }).filter(field => isInputField(field.type) && !['hidden', 'calculated', 'payment'].includes(field.type))
const filled = (value: unknown) => value != null && value !== '' && value !== false && !(Array.isArray(value) && !value.length)

function rowOf(form: StoredForm, entry: IndexedResponse, withAnswers: boolean): ResponseRow {
  const data = answersOf(form, entry)
  const questions = questionsOf(form)
  return {
    id: entry.id,
    number: entry.number,
    form: { id: form.id, name: form.name },
    submitted_at: new Date(entry.at).toISOString(),
    status: entry.status,
    tags: entry.tags,
    respondent: entry.respondent,
    channel: entry.channel,
    language: entry.language,
    duration_seconds: entry.duration_seconds,
    answers: withAnswers ? data : {},
    notes_count: entry.notes_count,
    answered: questions.filter(field => filled(data[field.key])).length,
    questions: questions.length,
    files_count: questions.filter(field => isFileField(field.type)).reduce((sum, field) => sum + (Array.isArray(data[field.key]) ? (data[field.key] as unknown[]).length : 0), 0),
    edited: entry.edited,
    possible_duplicate: entry.possible_duplicate,
  }
}

/** Status, tag, channel, date and search filters, then sort and one page. */
function pageOf(items: { form: StoredForm; entry: IndexedResponse }[], query: Query, searchAnswers: boolean) {
  const status = list(query, 'status')
  const tag = list(query, 'tag')
  const channel = list(query, 'channel')
  const forms = list(query, 'form')
  const flagged = query['filter[flag]'] === 'duplicate'
  const from = day(query.from, false)
  const to = day(query.to, true)
  const q = typeof query.q === 'string' ? query.q.trim().toLowerCase() : ''
  let result = items.filter(
    ({ form, entry }) =>
      (!status || status.includes(entry.status)) &&
      (!tag || entry.tags.some(item => tag.includes(item))) &&
      (!channel || channel.includes(entry.channel)) &&
      (!forms || forms.includes(form.id)) &&
      (!flagged || !!entry.possible_duplicate) &&
      (from === null || entry.at >= from) &&
      (to === null || entry.at <= to) &&
      (!q ||
        String(entry.number) === q.replace(/^#/, '') ||
        `${entry.respondent.name ?? ''} ${entry.respondent.email ?? ''} ${form.name}`.toLowerCase().includes(q) ||
        (searchAnswers && JSON.stringify(answersOf(form, entry)).toLowerCase().includes(q))),
  )
  const sort = typeof query.sort === 'string' && query.sort ? query.sort : '-submitted_at'
  const desc = sort.startsWith('-')
  const key = desc ? sort.slice(1) : sort
  const ORDER: Record<ResponseStatus, number> = { new: 0, reviewed: 1, approved: 2, rejected: 3 }
  const value = ({ form, entry }: { form: StoredForm; entry: IndexedResponse }): string | number =>
    key === 'number' ? entry.number : key === 'status' ? ORDER[entry.status] : key === 'respondent' ? (entry.respondent.name ?? entry.respondent.email ?? '~').toLowerCase() : key === 'form' ? form.name.toLowerCase() : entry.at
  result = [...result].sort((a, b) => {
    const x = value(a)
    const y = value(b)
    return (x < y ? -1 : x > y ? 1 : b.entry.at - a.entry.at) * (desc ? -1 : 1)
  })
  const page = Math.max(1, Number(query.page) || 1)
  const pageSize = Math.min(100, Math.max(1, Number(query.page_size) || 20))
  return {
    data: result.slice((page - 1) * pageSize, page * pageSize),
    meta: { page, page_size: pageSize, total: result.length, total_pages: Math.max(1, Math.ceil(result.length / pageSize)) },
  }
}

/** GET /forms/:id/responses, one form's responses with their answers. */
export const listFormResponses = defineMockRoute(({ event, query }) => {
  const { tenant, user } = requireAuth(event)
  const form = formFor(tenant, user, getRouterParam(event, 'id'))
  const { data, meta } = pageOf(formResponses(tenant, form).map(entry => ({ form, entry })), query, true)
  return ok(data.map(({ entry }) => rowOf(form, entry, true)), meta)
})

/** GET /forms/:id/responses/insights, the numbers and charts for one form. */
export const formInsights = defineMockRoute(({ event, query }) => {
  const { tenant, user } = requireAuth(event)
  const form = formFor(tenant, user, getRouterParam(event, 'id'))
  return ok(insightsOf(formResponses(tenant, form).map(entry => ({ form, entry })), query, form))
})

/** GET /responses, the inbox: every form this person may see. */
export const listResponses = defineMockRoute(({ event, query }) => {
  const { tenant, user } = requireAuth(event)
  const { data, meta } = pageOf(workspaceResponses(tenant, form => levelOf(form, user) !== 'none'), query, false)
  return ok(data.map(({ form, entry }) => rowOf(form, entry, false)), meta)
})

/**
 * GET /responses/forms, the Responses page grouped by form (owner 2026-10-04): one row per form the
 * person may see that has responses, with counts by review status, last response and a 30-day
 * trend. `q` (form name), `filter[form_status]`, `filter[folder_id]`, `filter[review]` (forms with
 * responses in that review status), sort `-new` (default) · `-last_at` · `-total` · `name`; paged.
 * With a review status asked for, the default sort counts that status instead (most approved first…),
 * so the sidebar's New / Reviewed / Approved / Rejected each give their own order.
 */
export const listResponseForms = defineMockRoute(({ event, query }) => {
  const { tenant, user } = requireAuth(event)
  const formStatus = list(query, 'form_status')
  const folder = list(query, 'folder_id')
  const review = list(query, 'review') as ResponseStatus[] | null
  const q = typeof query.q === 'string' ? query.q.trim().toLowerCase() : ''
  const today = Date.parse(new Date().toISOString().slice(0, 10))
  const rows: ResponseFormRow[] = []
  for (const form of formsOf(tenant).forms) {
    if (form.deleted_at || levelOf(form, user) === 'none') continue
    if ((formStatus && !formStatus.includes(form.status)) || (folder && !folder.includes(form.folder?.id ?? 'none')) || (q && !form.name.toLowerCase().includes(q))) continue
    const entries = formResponses(tenant, form)
    if (!entries.length) continue
    const counts: Record<ResponseStatus, number> = { new: 0, reviewed: 0, approved: 0, rejected: 0 }
    const daily = Array.from({ length: 30 }, () => 0)
    for (const entry of entries) {
      counts[entry.status]++
      const index = 29 - Math.floor((today + DAY - 1 - entry.at) / DAY)
      if (index >= 0 && index < 30) daily[index]!++
    }
    if (review && !review.some(status => counts[status] > 0)) continue
    rows.push({
      id: form.id,
      name: form.name,
      status: form.status,
      folder: form.folder,
      owner: { id: form.owner.id, name: form.owner.name },
      public_key: form.public_key,
      custom_link: form.custom_link ?? null,
      completion_rate: form.completion_rate,
      total: entries.length,
      status_counts: counts,
      last_at: new Date(entries[0]!.at).toISOString(),
      daily,
    })
  }
  const sort = typeof query.sort === 'string' && query.sort ? query.sort : '-new'
  const desc = sort.startsWith('-')
  const key = desc ? sort.slice(1) : sort
  const focus = (row: ResponseFormRow) => (review ?? ['new']).reduce((sum: number, status: ResponseStatus) => sum + (row.status_counts[status] ?? 0), 0)
  const value = (row: ResponseFormRow): string | number =>
    key === 'name' ? row.name.toLowerCase() : key === 'total' ? row.total : key === 'last_at' ? row.last_at ?? '' : key !== 'new' && key in row.status_counts ? row.status_counts[key as ResponseStatus] : focus(row)
  rows.sort((a, b) => {
    const x = value(a)
    const y = value(b)
    return (x < y ? -1 : x > y ? 1 : (b.last_at ?? '').localeCompare(a.last_at ?? '')) * (desc ? -1 : 1)
  })
  const page = Math.max(1, Number(query.page) || 1)
  const pageSize = Math.min(100, Math.max(1, Number(query.page_size) || 20))
  return ok(rows.slice((page - 1) * pageSize, page * pageSize), { page, page_size: pageSize, total: rows.length, total_pages: Math.max(1, Math.ceil(rows.length / pageSize)) })
})

/** GET /responses/insights, the inbox numbers. */
export const inboxInsights = defineMockRoute(({ event, query }) => {
  const { tenant, user } = requireAuth(event)
  return ok(insightsOf(workspaceResponses(tenant, form => canSee(form, user)), query))
})

export function responseFor(tenant: MockTenant, user: MockUser, id: string | undefined, need: 'responses' | 'edit') {
  const found = id ? findResponse(tenant, id) : null
  if (!found || found.form.deleted_at) throw new MockError('FRM-GEN-1004')
  requireLevel(found.form, user, need)
  return found
}

function detailOf(form: StoredForm, entry: IndexedResponse, user: MockUser): ResponseDetail {
  const schema = form.versions?.find(item => item.number === entry.form_version)?.schema ?? responseSchema(form)!
  const stored = entry.source.kind === 'real' ? entry.source.stored : null
  const ua = stored?.meta.user_agent ?? ''
  const device = stored ? (/mobile|android|iphone/i.test(ua) ? 'Phone' : /ipad|tablet/i.test(ua) ? 'Tablet' : 'Desktop') : ['Desktop', 'Phone', 'Phone', 'Tablet'][entry.number % 4]!
  const review = reviewOf(entry.id)
  const level = levelOf(form, user)
  return {
    ...rowOf(form, entry, false),
    data: answersOf(form, entry),
    form_version: entry.form_version,
    schema,
    meta: { device, country: null },
    notes: [...(review?.notes ?? [])].reverse(),
    history: review?.history ?? [],
    can: { review: level !== 'none', edit: level === 'edit' },
  }
}

/** GET /responses/:id, one response with every answer, notes and history. */
export const getResponse = defineMockRoute(({ event }) => {
  const { tenant, user } = requireAuth(event)
  const { form, entry } = responseFor(tenant, user, getRouterParam(event, 'id'), 'responses')
  return ok(detailOf(form, entry, user))
})

function audit(event: H3Event, tenant: MockTenant, user: MockUser, action: 'responses.updated' | 'responses.deleted', form: StoredForm, entry: IndexedResponse, changes: { field: string; before: unknown; after: unknown }[] = []) {
  recordAudit(event, tenant, {
    action,
    actor: actorOf(user),
    resource: { type: 'response', id: entry.id, name: `#${entry.number} · ${form.name}` },
    changes: changes.map(change => ({ field: change.field, before: change.before as never, after: change.after as never })),
  })
}

const patchBody = z.object({
  status: z.enum(RESPONSE_STATUSES as [ResponseStatus, ...ResponseStatus[]]).optional(),
  tags: z.array(z.string().trim().min(1).max(40)).max(20).optional(),
  /** Changed answers (key → value); needs "Can edit". */
  data: z.record(z.string().max(64), z.unknown()).optional(),
})

/** PATCH /responses/:id, status, tags, or (editors) answers; each change kept in the history. */
export const patchResponse = defineMockRoute(({ event, body: raw }) => {
  const { tenant, user } = requireAuth(event)
  const input = parseBody(patchBody, raw)
  const { form, entry } = responseFor(tenant, user, getRouterParam(event, 'id'), input.data ? 'edit' : 'responses')
  const current = answersOf(form, entry)
  const by = { id: user.id, name: `${user.first_name} ${user.last_name}`.trim() }
  const at = new Date().toISOString()
  const changes: { field: string; before: unknown; after: unknown }[] = []
  if (input.status && input.status !== entry.status) changes.push({ field: 'status', before: entry.status, after: input.status })
  const tags = input.tags ? [...new Set(input.tags)] : null
  if (tags && JSON.stringify(tags) !== JSON.stringify(entry.tags)) changes.push({ field: 'tags', before: entry.tags, after: tags })
  for (const [key, value] of Object.entries(input.data ?? {}))
    if (JSON.stringify(current[key] ?? null) !== JSON.stringify(value ?? null)) changes.push({ field: `answer:${key}`, before: current[key] ?? null, after: value ?? null })
  if (changes.length) {
    updateReview(form.id, entry.id, review => {
      if (input.status) review.status = input.status
      if (tags) review.tags = tags
      if (input.data) review.data = { ...review.data, ...input.data }
      review.history = [...changes.map(change => ({ id: crypto.randomUUID(), at, by, ...change })), ...(review.history ?? [])].slice(0, 200)
    })
    audit(event, tenant, user, 'responses.updated', form, entry, changes)
  }
  const updated = findResponse(tenant, entry.id)!
  return ok(detailOf(updated.form, updated.entry, user))
})

const noteBody = z.object({ text: z.string().trim().min(1).max(2000) })

/** POST /responses/:id/notes, a note for the team (never shown to the respondent). */
export const addNote = defineMockRoute(({ event, body: raw }) => {
  const { tenant, user } = requireAuth(event)
  const input = parseBody(noteBody, raw)
  const { form, entry } = responseFor(tenant, user, getRouterParam(event, 'id'), 'responses')
  updateReview(form.id, entry.id, review => {
    review.notes = [...(review.notes ?? []), { id: crypto.randomUUID(), author: { id: user.id, name: `${user.first_name} ${user.last_name}`.trim() }, text: input.text, created_at: new Date().toISOString() }]
  })
  audit(event, tenant, user, 'responses.updated', form, entry, [{ field: 'note', before: null, after: 'added' }])
  const updated = findResponse(tenant, entry.id)!
  return ok(detailOf(updated.form, updated.entry, user))
})

/** DELETE /responses/:id, removed for good (editors only). */
export const deleteResponse = defineMockRoute(({ event }) => {
  const { tenant, user } = requireAuth(event)
  const { form, entry } = responseFor(tenant, user, getRouterParam(event, 'id'), 'edit')
  updateReview(form.id, entry.id, review => (review.deleted_at = new Date().toISOString()))
  formResponses(tenant, form)
  audit(event, tenant, user, 'responses.deleted', form, entry)
  return ok({ deleted: 1 })
})

const bulkBody = z.object({
  ids: z.array(z.string().max(64)).min(1).max(500),
  action: z.enum(['status', 'tag', 'untag', 'delete']),
  value: z.string().trim().max(40).optional(),
})

/** POST /responses/bulk, the same change for many (those the person may not change are skipped). */
export const bulkResponses = defineMockRoute(({ event, body: raw }) => {
  const { tenant, user } = requireAuth(event)
  const input = parseBody(bulkBody, raw)
  if (input.action === 'status' && !RESPONSE_STATUSES.includes(input.value as ResponseStatus)) throw new MockError('FRM-GEN-1002', [{ field: 'value', message: 'Unknown status.' }])
  if ((input.action === 'tag' || input.action === 'untag') && !input.value) throw new MockError('FRM-GEN-1002', [{ field: 'value', message: 'Tag required.' }])
  let done = 0
  let skipped = 0
  const touched = new Set<StoredForm>()
  for (const id of input.ids) {
    const found = findResponse(tenant, id)
    const level = found ? levelOf(found.form, user) : 'none'
    if (!found || level === 'none' || (input.action === 'delete' && level !== 'edit')) {
      skipped++
      continue
    }
    const { form, entry } = found
    if (input.action === 'delete') {
      updateReview(form.id, entry.id, review => (review.deleted_at = new Date().toISOString()))
      audit(event, tenant, user, 'responses.deleted', form, entry)
    } else {
      const field = input.action === 'status' ? 'status' : 'tags'
      const after = input.action === 'status' ? input.value : input.action === 'tag' ? [...new Set([...entry.tags, input.value!])] : entry.tags.filter(tag => tag !== input.value)
      const before = input.action === 'status' ? entry.status : entry.tags
      if (JSON.stringify(before) !== JSON.stringify(after)) {
        const by = { id: user.id, name: `${user.first_name} ${user.last_name}`.trim() }
        updateReview(form.id, entry.id, review => {
          if (input.action === 'status') review.status = input.value as ResponseStatus
          else review.tags = after as string[]
          review.history = [{ id: crypto.randomUUID(), at: new Date().toISOString(), by, field, before, after }, ...(review.history ?? [])].slice(0, 200)
        })
        audit(event, tenant, user, 'responses.updated', form, entry, [{ field, before, after }])
      }
    }
    touched.add(form)
    done++
  }
  for (const form of touched) formResponses(tenant, form)
  return ok({ done, skipped })
})

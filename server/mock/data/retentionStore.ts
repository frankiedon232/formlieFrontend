/**
 * Privacy in the mock (F14 M5, data/retentionStore.ts): retention removes responses older than their form's limit (the form's
 * own, else the workspace's), for good, like a delete in the portal; it runs when the setting is saved
 * and once a day after that. Data requests find one person's responses by their email anywhere in the
 * workspace (the respondent's email, or any answer that is exactly that address).
 */
import type { H3Event } from 'h3'
import { allFields } from '#shared/utils/forms/build'
import { answerText } from '#shared/utils/forms/answer-text'
import { actorOf, recordAudit } from '../core/audit'
import { emitResponse } from './integrationStore'
import { formsOf, type StoredForm } from './formStore'
import { answersOf, formResponses, responseSchema, type IndexedResponse } from './responseData'
import { updateReview } from './responseReview'
import { settingsOf } from './settingsStore'
import type { MockTenant, MockUser } from './tenants'

const DAY = 86_400_000
const lastRun = new Map<string, number>()

/** The limit in days for a form (0 = keep). */
export function retentionOf(tenant: MockTenant, form: StoredForm): number {
  const own = (responseSchema(form)?.settings as { retention_days?: number | null } | undefined)?.retention_days
  return own ?? settingsOf(tenant).privacy.retention_days
}

/** Responses past their limit, form by form (what retention would remove now). */
export function expiredResponses(tenant: MockTenant, override?: number): { form: StoredForm; entries: IndexedResponse[] }[] {
  const now = Date.now()
  return formsOf(tenant)
    .forms.filter(form => !form.deleted_at)
    .map(form => {
      const own = (responseSchema(form)?.settings as { retention_days?: number | null } | undefined)?.retention_days
      const days = own ?? override ?? settingsOf(tenant).privacy.retention_days
      return { form, entries: days ? formResponses(tenant, form).filter(entry => entry.at < now - days * DAY) : [] }
    })
    .filter(item => item.entries.length)
}

function remove(event: H3Event | null, tenant: MockTenant, form: StoredForm, entries: IndexedResponse[]) {
  const at = new Date().toISOString()
  for (const entry of entries) updateReview(form.id, entry.id, review => (review.deleted_at = at))
  formResponses(tenant, form)
  if (event) for (const entry of entries.slice(0, 50)) emitResponse(event, tenant, 'response.deleted', form, entry.id)
}

/** Removes what is past its limit; `user` when someone saved the setting (else Formalie, daily). Returns how many. */
export function applyRetention(event: H3Event | null, tenant: MockTenant, user?: MockUser): number {
  lastRun.set(tenant.id, Date.now())
  const due = expiredResponses(tenant)
  let removed = 0
  for (const { form, entries } of due) {
    remove(event, tenant, form, entries)
    removed += entries.length
  }
  if (removed && event)
    recordAudit(event, tenant, {
      action: 'settings.retention_applied',
      actor: user ? actorOf(user) : { type: 'system', id: null, name: 'Formalie', email: null },
      resource: { type: 'setting', id: null, name: 'Privacy and data' },
      metadata: { responses: String(removed), forms: String(due.length) },
    })
  return removed
}

/** Once a day per workspace (the mock has no scheduler; called when lists are read). */
export function applyRetentionDaily(event: H3Event | null, tenant: MockTenant) {
  if (Date.now() - (lastRun.get(tenant.id) ?? 0) < DAY) return
  applyRetention(event, tenant)
}

// ── Data requests ─────────────────────────────────────────────────────────────────────

export const normaliseEmail = (value: string) => value.trim().toLowerCase()

/** One person's responses: the respondent's email, or an answer that is exactly that address. */
export function responsesOfPerson(tenant: MockTenant, email: string): { form: StoredForm; entry: IndexedResponse }[] {
  const wanted = normaliseEmail(email)
  const found: { form: StoredForm; entry: IndexedResponse }[] = []
  for (const form of formsOf(tenant).forms.filter(item => !item.deleted_at))
    for (const entry of formResponses(tenant, form)) {
      const own = entry.respondent.email && normaliseEmail(entry.respondent.email) === wanted
      const inAnswers = !own && entry.source.kind === 'real' && Object.values(answersOf(form, entry)).some(value => typeof value === 'string' && normaliseEmail(value) === wanted)
      if (own || inAnswers) found.push({ form, entry })
    }
  return found
}

/** Everything about one person, readable: form, number, when, answers by question. */
export function exportPerson(tenant: MockTenant, email: string) {
  return {
    email: normaliseEmail(email),
    exported_at: new Date().toISOString(),
    responses: responsesOfPerson(tenant, email).map(({ form, entry }) => {
      const schema = responseSchema(form)
      const answers = answersOf(form, entry)
      const fields = schema ? allFields(schema).filter(field => field.key in answers) : []
      return {
        form: form.name,
        number: entry.number,
        submitted_at: new Date(entry.at).toISOString(),
        language: entry.language,
        answers: Object.fromEntries(fields.map(field => [field.label?.trim() || field.key, answerText(field, answers[field.key])])),
      }
    }),
  }
}

export function deletePerson(event: H3Event, tenant: MockTenant, email: string): { responses: number; forms: number } {
  const found = responsesOfPerson(tenant, email)
  const byForm = new Map<StoredForm, IndexedResponse[]>()
  for (const { form, entry } of found) byForm.set(form, [...(byForm.get(form) ?? []), entry])
  for (const [form, entries] of byForm) remove(event, tenant, form, entries)
  return { responses: found.length, forms: byForm.size }
}

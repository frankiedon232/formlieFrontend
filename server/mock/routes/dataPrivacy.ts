/**
 * Privacy and data (F14 M5, docs/API-CONTRACT.md → Settings). Admins only.
 *
 *   GET  /settings/privacy/retention-preview?days=   what that limit would remove now
 *   POST /privacy/requests/search   { email }                → DataRequestMatch
 *   POST /privacy/requests/export   { email }                → everything about that person (JSON)
 *   POST /privacy/requests/delete   { email, confirm }       → removes all their responses (confirm = the email again)
 *
 * Exports and deletions are in the audit trail with the address masked.
 */
import { z } from 'zod'
import type { DataRequestMatch, RetentionDays, RetentionPreview } from '#shared/types/privacy'
import { RETENTION_DAYS } from '#shared/types/privacy'
import { actorOf, recordAudit } from '../core/audit'
import { requireAdmin } from '../core/auth'
import { MockError, ok } from '../core/respond'
import { defineMockRoute } from '../core/route'
import { parseBody } from '../core/validate'
import { deletePerson, expiredResponses, exportPerson, normaliseEmail, responsesOfPerson } from '../data/retentionStore'

const masked = (email: string) => {
  const [name = '', domain = ''] = email.split('@')
  return `${name.slice(0, 1)}•••@${domain}`
}

export const retentionPreview = defineMockRoute(({ event, query }) => {
  const { tenant } = requireAdmin(event)
  const days = Number(query.days)
  if (!(RETENTION_DAYS as readonly number[]).includes(days)) throw new MockError('FRM-GEN-1002', [{ field: 'days', message: 'retention' }])
  const due = expiredResponses(tenant, days)
  const kept = due.flatMap(item => item.entries).reduce((max, entry) => Math.max(max, entry.at), 0)
  return ok<RetentionPreview>({ days: days as RetentionDays, responses: due.reduce((sum, item) => sum + item.entries.length, 0), forms: due.length, oldest_kept: kept ? new Date(kept).toISOString() : null })
})

const emailSchema = z.object({ email: z.email().max(200) })

export const searchRequest = defineMockRoute(({ event, body }) => {
  const { tenant } = requireAdmin(event)
  const { email } = parseBody(emailSchema, body)
  const found = responsesOfPerson(tenant, email)
  const forms = new Map<string, DataRequestMatch['forms'][number]>()
  for (const { form, entry } of found) {
    const item = forms.get(form.id) ?? { id: form.id, name: form.name, count: 0, latest: new Date(entry.at).toISOString() }
    item.count++
    if (entry.at > Date.parse(item.latest)) item.latest = new Date(entry.at).toISOString()
    forms.set(form.id, item)
  }
  return ok<DataRequestMatch>({ email: normaliseEmail(email), total: found.length, forms: [...forms.values()].sort((a, b) => b.count - a.count) })
})

export const exportRequest = defineMockRoute(({ event, body }) => {
  const { tenant, user } = requireAdmin(event)
  const { email } = parseBody(emailSchema, body)
  const data = exportPerson(tenant, email)
  recordAudit(event, tenant, { action: 'settings.data_exported', actor: actorOf(user), resource: { type: 'person', id: null, name: masked(data.email) }, metadata: { responses: String(data.responses.length) } })
  return ok(data)
})

const deleteSchema = emailSchema.extend({ confirm: z.string().max(200) })

export const deleteRequest = defineMockRoute(({ event, body }) => {
  const { tenant, user } = requireAdmin(event)
  const input = parseBody(deleteSchema, body)
  if (normaliseEmail(input.confirm) !== normaliseEmail(input.email)) throw new MockError('FRM-GEN-1002', [{ field: 'confirm', message: 'confirm' }])
  const result = deletePerson(event, tenant, input.email)
  recordAudit(event, tenant, { action: 'settings.data_deleted', actor: actorOf(user), resource: { type: 'person', id: null, name: masked(normaliseEmail(input.email)) }, metadata: { responses: String(result.responses), forms: String(result.forms) } })
  return ok(result)
})

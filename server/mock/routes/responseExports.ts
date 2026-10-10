/**
 * Mock response exports (docs/API-CONTRACT.md → Responses → Exports, F11 M3). A form's responses
 * as a file: all of them, the ones matching the list's filters, or the selected ones; the table's
 * columns or every question; with or without review details. The file is made in the background
 * (progress), kept 7 days, and each download gets a one-time private link (5 minutes). The mock
 * writes a real .xlsx (core/xlsx.ts), CSV, and a designed PDF report (data/responseReport.ts).
 * Every export, download and removal is in the audit trail.
 */
import { z } from 'zod'
import type { H3Event } from 'h3'
import type { ResponseExport, ResponseExportFormat } from '#shared/types/responses'
import { answerText } from '#shared/utils/forms/answer-text'
import { appearanceInk } from '#shared/utils/settings/appearance-ink'
import { requireAuth, tenantOf } from '../core/auth'
import { actorOf, recordAudit } from '../core/audit'
import { xlsx } from '../core/xlsx'
import { MockError, ok, paginate } from '../core/respond'
import { defineMockRoute } from '../core/route'
import { parseBody } from '../core/validate'
import { formsOf } from '../data/formStore'
import { responsesAllowed } from '../data/formPermissions'
import { answersOf, formResponses, titleOf } from '../data/responseData'
import { responseReport } from '../data/responseReport'
import { settingsOf } from '../data/settingsStore'
import type { MockTenant, MockUser } from '../data/tenants'
import { filterResponses, formFor, questionsOf } from './responses'

const KEEP_MS = 7 * 24 * 60 * 60 * 1000
const LINK_MS = 5 * 60 * 1000

interface StoredExport extends Omit<ResponseExport, 'status' | 'progress'> {
  tenantId: string
  startedAt: number
  durationMs: number
  bytes: Uint8Array
  deleted?: boolean
}
const exports = new Map<string, StoredExport>()
const links = new Map<string, { exportId: string; expires: number }>()

const bodySchema = z.object({
  format: z.enum(['xlsx', 'csv', 'pdf']),
  scope: z.enum(['all', 'filtered', 'selected']),
  /** The list's filters (`filter[status]`, `q`, `from`…) for "filtered". */
  query: z.record(z.string(), z.union([z.string(), z.number()])).default({}),
  /** Response ids for "selected". */
  ids: z.array(z.string().max(64)).max(5000).default([]),
  /** Question keys in order (the table's columns); empty = every question. */
  columns: z.array(z.string().max(64)).max(500).default([]),
  /** Status, tags, channel, language, time taken and notes count. */
  details: z.boolean().default(true),
})

export const csvCell = (value: unknown) => {
  const text = value == null ? '' : String(value)
  // Leading = + - @ would run as a formula in spreadsheet apps (CSV injection).
  const safe = /^[=+\-@\t\r]/.test(text) ? `'${text}` : text
  return /[",\n\r]/.test(safe) ? `"${safe.replace(/"/g, '""')}"` : safe
}
const slug = (text: string) => text.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '').slice(0, 40) || 'form'

function view(item: StoredExport): ResponseExport {
  const { tenantId: _t, startedAt, durationMs, bytes: _b, deleted: _d, ...rest } = item
  const progress = Math.min(100, Math.round(((Date.now() - startedAt) / durationMs) * 100))
  const expired = Date.parse(item.expires_at) < Date.now()
  return { ...rest, progress, status: expired ? 'expired' : progress >= 100 ? 'ready' : Date.now() - startedAt < 300 ? 'queued' : 'running' }
}
const audit = (event: H3Event, tenant: MockTenant, user: MockUser, action: 'responses.exported' | 'responses.export_downloaded' | 'responses.export_deleted', item: StoredExport) =>
  recordAudit(event, tenant, {
    action,
    actor: actorOf(user),
    resource: { type: 'export', id: item.id, name: item.file_name },
    metadata: { form: item.form.name, format: item.format, scope: item.scope, rows: String(item.rows) },
  })

/** POST /forms/:id/responses/export, start an export of this form's responses. */
export const exportFormResponses = defineMockRoute(({ event, body: raw }) => {
  const { tenant, user } = requireAuth(event)
  const form = formFor(tenant, user, getRouterParam(event, 'id'), 'export')
  const input = parseBody(bodySchema, raw)
  const all = formResponses(tenant, form).map(entry => ({ form, entry }))
  const query = Object.fromEntries(Object.entries(input.query).map(([key, value]) => [key, String(value)]))
  const picked =
    input.scope === 'selected'
      ? all.filter(item => input.ids.includes(item.entry.id))
      : filterResponses(all, input.scope === 'filtered' ? query : {}, true)
  if (!picked.length) throw new MockError('FRM-GEN-1002', [{ field: 'scope', message: 'Nothing to export.' }])

  const questions = questionsOf(form)
  const byKey = new Map(questions.map(field => [field.key, field]))
  const fields = input.columns.length ? input.columns.map(key => byKey.get(key)).filter(field => !!field) : questions
  // Only what the form collected (owner 2026-10-09): name and email come as the form's own questions
  const head = ['Number', 'Submitted (UTC)', ...(input.details ? ['Status', 'Tags', 'Came in', 'Language', 'Time taken (s)', 'Notes'] : []), ...fields.map(field => field.label?.trim() || field.key)]
  const rows = picked.map(({ entry }) => {
    const data = answersOf(form, entry)
    return [
      entry.number,
      new Date(entry.at).toISOString(),
      ...(input.details ? [entry.status, entry.tags.join('; '), entry.channel, entry.language, entry.duration_seconds ?? '', entry.notes_count] : []),
      ...fields.map(field => answerText(field, data[field.key])),
    ]
  })

  const stamp = new Date().toISOString().slice(0, 10)
  const extension: Record<ResponseExportFormat, string> = { csv: 'csv', xlsx: 'xlsx', pdf: 'pdf' }
  const file_name = `${slug(form.name)}-responses-${stamp}.${extension[input.format]}`
  let bytes: Uint8Array
  if (input.format === 'pdf') {
    // A designed report (owner 2026-10-05), not a text dump.
    const counts = { new: 0, reviewed: 0, approved: 0, rejected: 0 }
    for (const { entry } of picked) counts[entry.status]++
    // The application's own look (owner 2026-10-05), not the form's theme: the workspace's Appearance
    // colour (black and white = the portal's ink) with the app's status colours.
    const settings = settingsOf(tenant)
    const brand = appearanceInk(settings.appearance, settings.branding.brand_color)
    const SCOPE = { all: 'All responses', filtered: 'Matching the filters', selected: 'Selected responses' }
    bytes = responseReport({
      org: tenant.name,
      form: form.name,
      brand,
      exportedBy: `${user.first_name} ${user.last_name}`.trim(),
      exportedAt: new Date(),
      scope: SCOPE[input.scope],
      counts,
      responses: picked.map(({ entry }) => {
        const data = answersOf(form, entry)
        const at = new Date(entry.at)
        return {
          number: entry.number,
          name: titleOf(form, entry, data) ?? '',
          email: entry.respondent.name ? (entry.respondent.email ?? '') : '',
          submitted: `${at.toISOString().slice(0, 10)} ${at.toISOString().slice(11, 16)} UTC`,
          status: entry.status,
          channel: entry.channel,
          tags: input.details ? entry.tags : [],
          answers: fields.map(field => ({ question: field.label?.trim() || field.key, answer: answerText(field, data[field.key]) })),
        }
      }),
    })
  } else if (input.format === 'xlsx') {
    bytes = xlsx(form.name, [head, ...rows])
  } else {
    // Byte-order mark so spreadsheet apps open UTF-8 (accents, non-Latin names) correctly.
    bytes = new TextEncoder().encode(`${String.fromCharCode(0xfeff)}${[head, ...rows].map(row => row.map(csvCell).join(',')).join('\r\n')}\r\n`)
  }
  const now = Date.now()
  const item: StoredExport = {
    id: crypto.randomUUID(),
    form: { id: form.id, name: form.name },
    format: input.format,
    scope: input.scope,
    rows: rows.length,
    columns: fields.length,
    file_name,
    size: bytes.length,
    created_by: { id: user.id, name: `${user.first_name} ${user.last_name}`.trim() },
    created_at: new Date(now).toISOString(),
    expires_at: new Date(now + KEEP_MS).toISOString(),
    tenantId: tenant.id,
    startedAt: now,
    durationMs: 1200 + Math.min(5000, rows.length * 3),
    bytes,
  }
  exports.set(item.id, item)
  audit(event, tenant, user, 'responses.exported', item)
  return ok(view(item), {}, 202)
})

/** The exports this person may see: those of forms whose responses they can see. */
function visible(tenant: MockTenant, user: MockUser) {
  const forms = new Map(formsOf(tenant).forms.map(form => [form.id, form]))
  return [...exports.values()].filter(item => {
    const form = forms.get(item.form.id)
    return item.tenantId === tenant.id && !item.deleted && !!form && responsesAllowed(form, user, 'export')
  })
}
function findExport(tenant: MockTenant, user: MockUser, id: string | undefined) {
  const item = visible(tenant, user).find(entry => entry.id === id)
  if (!item) throw new MockError('FRM-GEN-1004')
  return item
}

/** GET /responses/exports, the Exports page: filter[format], filter[status] (ready / expired), filter[form], from / to (made in that period), q, sort, paged. */
export const listResponseExports = defineMockRoute(({ event, query }) => {
  const { tenant, user } = requireAuth(event)
  const pick = (key: string) => (typeof query[`filter[${key}]`] === 'string' && query[`filter[${key}]`] ? String(query[`filter[${key}]`]).split(',') : null)
  const formats = pick('format')
  const statuses = pick('status')
  const formIds = pick('form')
  const day = (value: unknown, end: boolean) => (typeof value === 'string' && /^\d{4}-\d{2}-\d{2}$/.test(value) ? Date.parse(value) + (end ? 86_400_000 - 1 : 0) : null)
  const from = day(query.from, false)
  const to = day(query.to, true)
  const items = visible(tenant, user)
    .map(view)
    .filter(item => (!formats || formats.includes(item.format)) && (!statuses || statuses.includes(item.status === 'running' || item.status === 'queued' ? 'running' : item.status)) && (!formIds || formIds.includes(item.form.id)) && (from === null || Date.parse(item.created_at) >= from) && (to === null || Date.parse(item.created_at) <= to))
  const { data, meta } = paginate(items, { sort: '-created_at', ...query }, (item, q) => item.file_name.toLowerCase().includes(q) || item.form.name.toLowerCase().includes(q))
  return ok(data, meta)
})

/** GET /responses/exports/:id, progress of one export. */
export const getResponseExport = defineMockRoute(({ event }) => {
  const { tenant, user } = requireAuth(event)
  return ok(view(findExport(tenant, user, getRouterParam(event, 'id'))))
})

/** POST /responses/exports/:id/link, a one-time private download link (5 minutes). */
export const responseExportLink = defineMockRoute(({ event }) => {
  const { tenant, user } = requireAuth(event)
  const item = findExport(tenant, user, getRouterParam(event, 'id'))
  const state = view(item)
  if (state.status === 'expired') throw new MockError('FRM-GEN-1004')
  if (state.status !== 'ready') throw new MockError('FRM-GEN-1002', [{ field: 'status', message: 'The file is still being made.' }])
  const token = crypto.randomUUID().replace(/-/g, '') + crypto.randomUUID().replace(/-/g, '')
  links.set(token, { exportId: item.id, expires: Date.now() + LINK_MS })
  audit(event, tenant, user, 'responses.export_downloaded', item)
  return ok({ url: `/api/v1/response-exports/${token}`, expires_at: new Date(Date.now() + LINK_MS).toISOString() })
})

/** DELETE /responses/exports/:id, the file is removed for good. */
export const deleteResponseExport = defineMockRoute(({ event }) => {
  const { tenant, user } = requireAuth(event)
  const item = findExport(tenant, user, getRouterParam(event, 'id'))
  item.deleted = true
  item.bytes = new Uint8Array()
  audit(event, tenant, user, 'responses.export_deleted', item)
  return ok({ id: item.id })
})

/** GET /response-exports/:token, the file (a browser download cannot carry the envelope); one use. */
export const downloadResponseExport = defineEventHandler(event => {
  const token = getRouterParam(event, 'token') ?? ''
  const link = links.get(token)
  const item = link ? exports.get(link.exportId) : undefined
  const host = tenantOf(event)
  // Browser downloads can't send the dev tenant header, so localhost / LAN addresses skip the host check.
  const isLocal = host.context.kind === 'manage' && host.context.reason === 'local'
  if (!link || !item || item.deleted || link.expires < Date.now() || Date.parse(item.expires_at) < Date.now() || (!isLocal && host.tenant?.id !== item.tenantId)) {
    setResponseStatus(event, 410)
    setHeader(event, 'content-type', 'text/plain; charset=utf-8')
    return 'This download link has expired. Download the export again from Responses → Exports.'
  }
  links.delete(token)
  const TYPES = { pdf: 'application/pdf', xlsx: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', csv: 'text/csv; charset=utf-8' }
  setHeader(event, 'content-type', TYPES[item.format])
  setHeader(event, 'content-disposition', `attachment; filename="${item.file_name}"`)
  setHeader(event, 'cache-control', 'no-store')
  return item.bytes
})

/** Finished exports of a workspace that are still downloadable (notifications: "Your export is ready"). */
export const readyExports = (tenantId: string) => [...exports.values()].filter(item => item.tenantId === tenantId && !item.deleted).map(view).filter(item => item.status === 'ready')

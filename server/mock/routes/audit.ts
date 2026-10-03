import { z } from 'zod'
import type { AuditEvent, AuditFacets, ExportJob } from '#shared/types/audit'
import { requireAdmin, tenantOf } from '../core/auth'
import { actorOf, auditLogOf, recordAudit } from '../core/audit'
import { MockError, ok, paginate } from '../core/respond'
import { defineMockRoute } from '../core/route'
import { parseBody } from '../core/validate'

type Query = Record<string, unknown>

const list = (query: Query, key: string) => {
  const value = query[`filter[${key}]`]
  return typeof value === 'string' && value ? value.split(',') : null
}
const day = (value: unknown, end: boolean) =>
  typeof value === 'string' && value ? Date.parse(`${value}T${end ? '23:59:59' : '00:00:00'}Z`) : null

/** Filters from API-CONTRACT.md → Audit trail (shared by the list and the export). */
function filterEvents(events: AuditEvent[], query: Query): AuditEvent[] {
  const area = list(query, 'area')
  const action = list(query, 'action')
  const outcome = list(query, 'outcome')
  const actor = list(query, 'actor_id')
  const country = list(query, 'country')
  const resourceType = list(query, 'resource_type')
  const resourceId = list(query, 'resource_id')
  const from = day(query.from, false)
  const to = day(query.to, true)
  return events.filter(event => {
    const at = Date.parse(event.occurred_at)
    return (
      (!area || area.includes(event.area)) &&
      (!action || action.includes(event.action)) &&
      (!outcome || outcome.includes(event.outcome)) &&
      (!actor || (event.actor.id !== null && actor.includes(event.actor.id))) &&
      (!country || country.includes(event.location.country ?? '')) &&
      (!resourceType || resourceType.includes(event.resource?.type ?? '')) &&
      (!resourceId || resourceId.includes(event.resource?.id ?? '')) &&
      (from === null || at >= from) &&
      (to === null || at <= to)
    )
  })
}

const matches = (event: AuditEvent, q: string) =>
  [
    event.actor.name,
    event.actor.email,
    event.resource?.name,
    event.location.ip,
    event.location.city,
    event.request_id,
    event.action,
  ].some(value => value?.toLowerCase().includes(q))

/** GET /audit-logs — admins only until Roles & access (F21). */
export const listAuditLogs = defineMockRoute(({ event, query }) => {
  const { tenant } = requireAdmin(event)
  const { data, meta } = paginate(
    filterEvents(auditLogOf(tenant), query),
    { sort: '-occurred_at', ...query },
    matches,
  )
  return ok(data, meta)
})

/** GET /audit-logs/facets — people and countries that appear in this workspace's trail. */
export const auditFacets = defineMockRoute(({ event }) => {
  const { tenant } = requireAdmin(event)
  const actors = new Map<string, string>()
  const countries = new Set<string>()
  for (const entry of auditLogOf(tenant)) {
    if (entry.actor.id) actors.set(entry.actor.id, entry.actor.name)
    if (entry.location.country) countries.add(entry.location.country)
  }
  return ok<AuditFacets>({
    actors: [...actors].map(([id, name]) => ({ id, name })).sort((a, b) => a.name.localeCompare(b.name)),
    countries: [...countries].sort(),
  })
})

/** GET /audit-logs/:id */
export const getAuditLog = defineMockRoute(({ event }) => {
  const { tenant } = requireAdmin(event)
  const id = getRouterParam(event, 'id')
  const entry = auditLogOf(tenant).find(item => item.id === id)
  if (!entry) throw new MockError('FRM-GEN-1004')
  return ok(entry)
})

// ── Export: background job + one-time download link ─────────────────────────────────

interface MockJob extends ExportJob {
  tenantId: string
  startedAt: number
  durationMs: number
  content: string
  token: string
}

const jobs = new Map<string, MockJob>()
const DOWNLOAD_TTL_MS = 10 * 60 * 1000

const exportSchema = z.object({
  format: z.enum(['xlsx', 'csv']),
  filters: z.record(z.string(), z.union([z.string(), z.number()])).default({}),
})

const csvCell = (value: unknown) => {
  const text = value == null ? '' : String(value)
  // Leading = + - @ would run as a formula in spreadsheet apps (CSV injection).
  const safe = /^[=+\-@\t\r]/.test(text) ? `'${text}` : text
  return /[",\n\r]/.test(safe) ? `"${safe.replace(/"/g, '""')}"` : safe
}

function toCsv(events: AuditEvent[]): string {
  const header = [
    'Time (UTC)',
    'Action',
    'Outcome',
    'Person',
    'Email',
    'Item type',
    'Item',
    'Changes',
    'IP address',
    'City',
    'Country',
    'Device',
    'Reason',
    'Request ID',
  ]
  const rows = events.map(event => [
    event.occurred_at,
    event.action,
    event.outcome,
    event.actor.name,
    event.actor.email,
    event.resource?.type,
    event.resource?.name,
    event.changes.map(c => `${c.field}: ${c.before ?? '—'} → ${c.after ?? '—'}`).join('; '),
    event.location.ip,
    event.location.city,
    event.location.country,
    [event.device.browser, event.device.os].filter(Boolean).join(' / '),
    event.reason,
    event.request_id,
  ])
  // Byte-order mark so spreadsheet apps open UTF-8 (accents, non-Latin names) correctly.
  const BOM = String.fromCharCode(0xfeff)
  return `${BOM}${[header, ...rows].map(row => row.map(csvCell).join(',')).join('\r\n')}\r\n`
}

function jobView(job: MockJob): ExportJob {
  const elapsed = Date.now() - job.startedAt
  const progress = Math.min(100, Math.round((elapsed / job.durationMs) * 100))
  const done = progress >= 100
  return {
    id: job.id,
    status: done ? 'done' : elapsed < 300 ? 'queued' : 'running',
    progress,
    rows: job.rows,
    format: job.format,
    file_name: job.file_name,
    download_url: done ? `/api/v1/downloads/${job.token}` : null,
    expires_at: done ? new Date(job.startedAt + job.durationMs + DOWNLOAD_TTL_MS).toISOString() : null,
  }
}

/** POST /audit-logs/export — same filters as the list; recorded in the trail itself. */
export const exportAuditLogs = defineMockRoute(({ event, body }) => {
  const { user, tenant } = requireAdmin(event)
  const input = parseBody(exportSchema, body)
  const query = Object.fromEntries(Object.entries(input.filters).map(([k, v]) => [k, String(v)]))
  let events = filterEvents(auditLogOf(tenant), query)
  const q = typeof query.q === 'string' ? query.q.trim().toLowerCase() : ''
  if (q) events = events.filter(item => matches(item, q))

  const stamp = new Date().toISOString().slice(0, 10)
  const job: MockJob = {
    id: crypto.randomUUID(),
    status: 'queued',
    progress: 0,
    rows: events.length,
    format: input.format,
    // The mock writes CSV for both choices; the real backend produces a true .xlsx file.
    file_name: `audit-trail-${tenant.subdomain}-${stamp}.csv`,
    download_url: null,
    expires_at: null,
    tenantId: tenant.id,
    startedAt: Date.now(),
    durationMs: 1500 + Math.min(4000, events.length * 4),
    content: toCsv(events),
    token: crypto.randomUUID().replace(/-/g, '') + crypto.randomUUID().replace(/-/g, ''),
  }
  jobs.set(job.id, job)
  recordAudit(event, tenant, {
    action: 'audit.exported',
    actor: actorOf(user),
    resource: { type: 'export', id: job.id, name: job.file_name },
    metadata: { format: input.format, rows: String(events.length) },
  })
  return ok(jobView(job), {}, 202)
})

/** GET /exports/:id — progress of an export job. */
export const getExportJob = defineMockRoute(({ event }) => {
  const { tenant } = requireAdmin(event)
  const job = jobs.get(getRouterParam(event, 'id') ?? '')
  if (!job || job.tenantId !== tenant.id) throw new MockError('FRM-GEN-1004')
  return ok(jobView(job))
})

/**
 * GET /downloads/:token — plain file response (a browser download cannot carry the envelope).
 * The token is the permission: single use, 10 minutes, and only on the workspace that made it.
 */
export const download = defineEventHandler(event => {
  const token = getRouterParam(event, 'token') ?? ''
  const job = [...jobs.values()].find(item => item.token === token)
  const host = tenantOf(event)
  // Browser downloads cannot send the dev tenant header, so localhost / LAN IPs skip the host check.
  const isLocal = host.context.kind === 'manage' && host.context.reason === 'local'
  const sameWorkspace = isLocal || host.tenant?.id === job?.tenantId
  const view = job ? jobView(job) : null
  if (
    !job ||
    !view ||
    view.status !== 'done' ||
    !sameWorkspace ||
    Date.parse(view.expires_at!) < Date.now()
  ) {
    setResponseStatus(event, 410)
    setHeader(event, 'content-type', 'text/plain; charset=utf-8')
    return 'This download link has expired. Start a new export.'
  }
  job.token = ''
  setHeader(event, 'content-type', 'text/csv; charset=utf-8')
  setHeader(event, 'content-disposition', `attachment; filename="${job.file_name}"`)
  setHeader(event, 'cache-control', 'no-store')
  return job.content
})

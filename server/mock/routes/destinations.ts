/**
 * Mock response storage API (F12 M2, docs/API-CONTRACT.md → Response storage). Admins only until
 * Roles & access (F22), like connections.
 *
 *   GET    /forms/:id/storage                   where the form's responses are kept + its fields
 *   GET    /datasources/:id/tables              tables Formalie may see on a connection
 *   GET    /destinations                        every form that stores in a database
 *   GET    /destinations/insights               the two chart cards
 *   POST   /destinations                        set up (creates the table, or maps an existing one)
 *   GET    /destinations/:id                    detail (columns, new fields, backfill)
 *   PATCH  /destinations/:id                    settings, columns, pause / resume
 *   POST   /destinations/:id/columns            add columns for fields added to the form
 *   GET    /destinations/:id/deliveries         every response with its delivery (status filter)
 *   POST   /destinations/:id/retry              retry failed deliveries (all, or some)
 *   POST   /destinations/:id/backfill           send earlier responses (date range) with progress
 *   DELETE /destinations/:id                    back to Formalie's storage (the table stays)
 */
import { z } from 'zod'
import { META_COLUMNS, type DestinationColumn, type DestinationInsights, type FormStorage } from '#shared/types/destinations'
import { tablesSchemaOf } from '#shared/utils/datasources/permissions'
import { blocking, checkMapping, checkTableRest, columnNameFor, columnTypeFor, standardSettings, typedForEngine } from '#shared/utils/datasources/tables'
import { actorOf, recordAudit } from '../core/audit'
import { requireAdmin, requireAuth } from '../core/auth'
import { MockError, ok, paginate, filtersOf } from '../core/respond'
import { defineMockRoute } from '../core/route'
import { parseBody } from '../core/validate'
import { tablesOf } from '../data/databaseTables'
import { dataSourcesOf } from '../data/dataSourceStore'
import { backfillState, createdTablesOn, deliveriesOf, destinationsOf, detailOfDestination, inputFieldsOf, rowOfDestination, saveDestinations, type StoredDestination } from '../data/destinationStore'
import { canSee } from '../data/formPermissions'
import { formsOf } from '../data/formStore'
import type { MockTenant } from '../data/tenants'

const DAY = 86_400_000
const columnSchema = z.object({
  column: z.string().trim().min(1).max(128),
  type: z.string().trim().min(1).max(64),
  source: z.union([z.object({ kind: z.literal('field'), key: z.string().min(1).max(128) }), z.object({ kind: z.literal('meta'), key: z.enum(META_COLUMNS) }), z.null()]),
  nullable: z.boolean(),
  existing: z.boolean(),
})
const settingsSchema = z.object({
  write_mode: z.enum(['insert', 'upsert']),
  key_column: z.string().trim().min(1).max(128),
  multi_value: z.enum(['json', 'text']),
  choices: z.enum(['value', 'label']),
})
const createSchema = z.object({
  form_id: z.string().min(1),
  datasource_id: z.string().min(1),
  table: z.object({ mode: z.enum(['create', 'existing']), schema: z.string().trim().max(128), name: z.string().trim().min(1).max(128) }),
  columns: z.array(columnSchema).min(1).max(500),
  settings: settingsSchema,
})

function findDestination(tenant: MockTenant, id: string | undefined): StoredDestination {
  const destination = destinationsOf(tenant).find(item => item.id === id)
  if (!destination) throw new MockError('FRM-GEN-1004')
  return destination
}
const formOf = (tenant: MockTenant, id: string) => formsOf(tenant).forms.find(form => form.id === id && !form.deleted_at)
const resource = (tenant: MockTenant, destination: StoredDestination) => ({ type: 'destination', id: destination.id, name: `${formOf(tenant, destination.form_id)?.name ?? ''} → ${destination.table.name}` })

/** Problems in a mapping → FRM-DEST-1016 with one detail per column. */
function checkColumns(columns: DestinationColumn[], fields: ReturnType<typeof inputFieldsOf>, settings: z.infer<typeof settingsSchema>) {
  const problems = blocking(checkMapping(columns, fields, settings))
  if (problems.length) throw new MockError('FRM-DEST-1016', problems.map(problem => ({ field: problem.column ?? 'response_id', message: problem.code })))
}

// ── A form's storage, a connection's tables ──────────────────────────────────────────────

export const formStorage = defineMockRoute(({ event }) => {
  const { tenant, user } = requireAuth(event)
  const form = formOf(tenant, getRouterParam(event, 'id') ?? '')
  if (!form || !canSee(form, user)) throw new MockError('FRM-GEN-1004')
  const destination = destinationsOf(tenant).find(item => item.form_id === form.id)
  return ok<FormStorage & { fields: { key: string; label: string; type: string; options?: { value: string; label: string }[] }[]; can_manage: boolean }>({
    mode: destination ? 'database' : 'formalie',
    destination: destination ? rowOfDestination(tenant, destination) : null,
    connections: dataSourcesOf(tenant).filter(source => source.enabled).length,
    fields: inputFieldsOf(form).map(field => ({ key: field.key, label: field.label ?? field.key, type: field.type, options: field.options?.map(option => ({ value: option.value, label: option.label })) })),
    can_manage: user.role !== 'member',
  })
})

export const listTables = defineMockRoute(({ event }) => {
  const { tenant } = requireAdmin(event)
  const source = dataSourcesOf(tenant).find(item => item.id === getRouterParam(event, 'id'))
  if (!source) throw new MockError('FRM-GEN-1004')
  return ok(tablesOf(source, createdTablesOn(tenant, source)))
})

// ── List, insights ───────────────────────────────────────────────────────────────────────

const inList = (value: unknown, actual: string) => typeof value !== 'string' || !value || value.split(',').includes(actual)

export const listDestinations = defineMockRoute(({ event, query }) => {
  const { tenant } = requireAdmin(event)
  const filter = filtersOf(query)
  const rows = destinationsOf(tenant)
    .map(item => rowOfDestination(tenant, item))
    .filter((row): row is NonNullable<typeof row> => !!row)
    .filter(row => inList(filter.status, row.status) && inList(filter.datasource, row.datasource.id) && inList(filter.table, row.table.created ? 'created' : 'existing'))
    .map(row => ({ ...row, form_name: row.form.name }))
  const { data, meta } = paginate(rows, { sort: 'form_name', ...query }, (row, q) => [row.form.name, row.datasource.name, row.table.name].some(text => text.toLowerCase().includes(q)))
  return ok(data, meta)
})

export const destinationInsights = defineMockRoute(({ event }) => {
  const { tenant } = requireAdmin(event)
  const rows = destinationsOf(tenant).map(item => rowOfDestination(tenant, item)).filter(row => !!row)
  const now = Date.now()
  const deliveries = { sent: 0, pending: 0, failed: 0, held: 0 }
  let previous = 0
  for (const item of destinationsOf(tenant)) {
    const form = formOf(tenant, item.form_id)
    if (!form) continue
    for (const delivery of deliveriesOf(tenant, item, form)) {
      const at = Date.parse(delivery.submitted_at)
      if (delivery.status === 'sent' && at < now - 30 * DAY && at >= now - 60 * DAY) previous++
      if (at < now - 30 * DAY || delivery.status === 'not_sent') continue
      deliveries[delivery.status]++
    }
  }
  const daily = rows[0]?.daily.map((day, i) => ({ date: day.date, count: rows.reduce((sum, row) => sum + row.daily[i]!.count, 0) })) ?? []
  return ok<DestinationInsights>({
    total: rows.length,
    by_status: { active: rows.filter(row => row.status === 'active').length, paused: rows.filter(row => row.status === 'paused').length, failing: rows.filter(row => row.status === 'failing').length },
    sent_30d: rows.reduce((sum, row) => sum + row.sent_30d, 0),
    previous_30d: previous,
    daily,
    deliveries,
  })
})

// ── Set up, read, change, remove ─────────────────────────────────────────────────────────

export const createDestination = defineMockRoute(({ event, body }) => {
  const { tenant, user } = requireAdmin(event)
  const input = parseBody(createSchema, body)
  const form = formOf(tenant, input.form_id)
  if (!form) throw new MockError('FRM-GEN-1004')
  if (destinationsOf(tenant).some(item => item.form_id === form.id)) throw new MockError('FRM-DEST-1015')
  const source = dataSourcesOf(tenant).find(item => item.id === input.datasource_id)
  if (!source) throw new MockError('FRM-GEN-1004')
  if (!source.enabled) throw new MockError('FRM-DEST-1009')
  const fields = inputFieldsOf(form)
  const tables = tablesOf(source, createdTablesOn(tenant, source))
  let table: StoredDestination['table']
  if (input.table.mode === 'existing') {
    if (source.access.other !== 'read_write') throw new MockError('FRM-DEST-1013')
    const found = tables.find(item => item.schema === input.table.schema && item.name === input.table.name && !item.formalie)
    if (!found) throw new MockError('FRM-GEN-1004')
    table = { schema: found.schema, name: found.name, created: false }
  } else {
    const schema = tablesSchemaOf(source.engine, source.settings, source.access)
    const prefix = source.engine === 'oracle' ? source.access.table_prefix.toUpperCase() : source.access.table_prefix
    const name = input.table.name.trim()
    const problem = name.startsWith(prefix) ? checkTableRest(source.engine, prefix, name.slice(prefix.length)) : 'required'
    if (problem) throw new MockError('FRM-GEN-1002', [{ field: 'table', message: problem }])
    if (tables.some(item => item.schema === schema && item.name.toLowerCase() === name.toLowerCase())) throw new MockError('FRM-DEST-1014', [{ field: 'table', message: 'taken' }])
    table = { schema, name, created: true }
  }
  // Tables Formalie creates get their types from the connection's engine, whatever the request says.
  const columns = table.created ? typedForEngine(source.engine, input.columns as DestinationColumn[], fields, input.settings.multi_value) : (input.columns as DestinationColumn[])
  // Tables Formalie creates always follow its standard (one row per response, by its id).
  if (table.created) input.settings = standardSettings(input.settings, columns)
  checkColumns(columns, fields, input.settings)
  const now = new Date().toISOString()
  const destination: StoredDestination = {
    id: crypto.randomUUID(),
    form_id: form.id,
    datasource_id: source.id,
    table,
    columns,
    settings: input.settings,
    paused_at: null,
    covers_from: now,
    backfill: null,
    overrides: {},
    created_by: { id: user.id, name: `${user.first_name} ${user.last_name}`.trim() },
    created_at: now,
    updated_at: now,
  }
  destinationsOf(tenant).push(destination)
  saveDestinations()
  const actor = actorOf(user)
  if (table.created) recordAudit(event, tenant, { action: 'data.table_created', actor, resource: { type: 'data_source', id: source.id, name: source.name }, metadata: { table: `${table.schema}.${table.name}`, columns: String(columns.length) } })
  recordAudit(event, tenant, { action: 'data.destination_created', actor, resource: resource(tenant, destination), metadata: { connection: source.name, table: `${table.schema}.${table.name}`, mode: table.created ? 'created' : 'existing' } })
  return ok(detailOfDestination(tenant, destination), {}, 201)
})

export const getDestination = defineMockRoute(({ event }) => {
  const { tenant } = requireAdmin(event)
  return ok(detailOfDestination(tenant, findDestination(tenant, getRouterParam(event, 'id'))))
})

export const patchDestination = defineMockRoute(({ event, body }) => {
  const { tenant, user } = requireAdmin(event)
  const destination = findDestination(tenant, getRouterParam(event, 'id'))
  const input = parseBody(z.object({ paused: z.boolean().optional(), settings: settingsSchema.optional(), columns: z.array(columnSchema).max(500).optional() }), body)
  const form = formOf(tenant, destination.form_id)
  if (!form) throw new MockError('FRM-GEN-1004')
  const actor = actorOf(user)
  if (input.paused !== undefined && input.paused !== !!destination.paused_at) {
    if (input.paused) destination.paused_at = new Date().toISOString()
    else {
      // Held responses go out now.
      const since = Date.parse(destination.paused_at!)
      for (const delivery of deliveriesOf(tenant, destination, form)) if (Date.parse(delivery.submitted_at) >= since && delivery.status === 'held') destination.overrides[delivery.response_id] = { status: 'pending', attempts: 0, retry_at: Date.now() + 2500, error_code: null }
      destination.paused_at = null
    }
    recordAudit(event, tenant, { action: input.paused ? 'data.destination_paused' : 'data.destination_resumed', actor, resource: resource(tenant, destination) })
  }
  if (input.settings || input.columns) {
    const source = dataSourcesOf(tenant).find(item => item.id === destination.datasource_id)
    const given = (input.columns as DestinationColumn[] | undefined) ?? destination.columns
    const columns = destination.table.created && source ? typedForEngine(source.engine, given, inputFieldsOf(form), destination.settings.multi_value) : given
    const asked = input.settings ?? destination.settings
    // How several values and choices are written is set when the table is set up (mixing would make the data inconsistent).
    const kept = { ...asked, multi_value: destination.settings.multi_value, choices: destination.settings.choices }
    const settings = destination.table.created ? standardSettings(kept, columns) : kept
    checkColumns(columns, inputFieldsOf(form), settings)
    destination.settings = settings
    destination.columns = columns
    recordAudit(event, tenant, { action: 'data.destination_updated', actor, resource: resource(tenant, destination) })
  }
  destination.updated_at = new Date().toISOString()
  saveDestinations()
  return ok(detailOfDestination(tenant, destination))
})

export const addColumns = defineMockRoute(({ event, body }) => {
  const { tenant, user } = requireAdmin(event)
  const destination = findDestination(tenant, getRouterParam(event, 'id'))
  const { keys } = parseBody(z.object({ keys: z.array(z.string().min(1)).min(1).max(200) }), body)
  const form = formOf(tenant, destination.form_id)
  const source = dataSourcesOf(tenant).find(item => item.id === destination.datasource_id)
  if (!form || !source) throw new MockError('FRM-GEN-1004')
  // Adding a column to a table of theirs needs Full access; Formalie's own tables always allow it.
  if (!destination.table.created && source.access.other !== 'read_write') throw new MockError('FRM-DEST-1013')
  const taken = new Set(destination.columns.map(column => column.column.toLowerCase()))
  const added: DestinationColumn[] = []
  for (const field of inputFieldsOf(form).filter(item => keys.includes(item.key))) {
    if (destination.columns.some(column => column.source?.kind === 'field' && column.source.key === field.key)) continue
    added.push({ column: columnNameFor(source.engine, field.key, taken), type: columnTypeFor(source.engine, field, destination.settings.multi_value), source: { kind: 'field', key: field.key }, nullable: true, existing: false })
  }
  destination.columns = [...destination.columns, ...added]
  destination.updated_at = new Date().toISOString()
  saveDestinations()
  if (added.length) recordAudit(event, tenant, { action: 'data.column_added', actor: actorOf(user), resource: resource(tenant, destination), metadata: { columns: added.map(column => column.column).join(', ') } })
  return ok(detailOfDestination(tenant, destination))
})

export const removeDestination = defineMockRoute(({ event }) => {
  const { tenant, user } = requireAdmin(event)
  const destination = findDestination(tenant, getRouterParam(event, 'id'))
  const list = destinationsOf(tenant)
  recordAudit(event, tenant, { action: 'data.destination_removed', actor: actorOf(user), resource: resource(tenant, destination), metadata: { table: `${destination.table.schema}.${destination.table.name}` } })
  list.splice(list.indexOf(destination), 1)
  saveDestinations()
  return ok({ removed: true })
})

// ── Deliveries, retries, backfill ────────────────────────────────────────────────────────

export const listDeliveries = defineMockRoute(({ event, query }) => {
  const { tenant } = requireAdmin(event)
  const destination = findDestination(tenant, getRouterParam(event, 'id'))
  const form = formOf(tenant, destination.form_id)
  if (!form) throw new MockError('FRM-GEN-1004')
  const filter = filtersOf(query)
  const rows = deliveriesOf(tenant, destination, form).filter(delivery => inList(filter.status, delivery.status))
  const { data, meta } = paginate(rows, { ...query, sort: undefined }, (row, q) => String(row.number).includes(q.replace('#', '')) || (row.respondent ?? '').toLowerCase().includes(q))
  return ok(data, meta)
})

export const retryDeliveries = defineMockRoute(({ event, body }) => {
  const { tenant, user } = requireAdmin(event)
  const destination = findDestination(tenant, getRouterParam(event, 'id'))
  const { response_ids } = parseBody(z.object({ response_ids: z.array(z.string()).max(5000).optional() }), body)
  const form = formOf(tenant, destination.form_id)
  if (!form) throw new MockError('FRM-GEN-1004')
  const failed = deliveriesOf(tenant, destination, form).filter(delivery => delivery.status === 'failed' && (!response_ids?.length || response_ids.includes(delivery.response_id)))
  for (const delivery of failed) destination.overrides[delivery.response_id] = { status: 'pending', attempts: delivery.attempts, retry_at: Date.now() + 2500, error_code: null }
  saveDestinations()
  recordAudit(event, tenant, { action: 'data.deliveries_retried', actor: actorOf(user), resource: resource(tenant, destination), metadata: { count: String(failed.length) } })
  return ok({ retried: failed.length })
})

export const startBackfill = defineMockRoute(({ event, body }) => {
  const { tenant, user } = requireAdmin(event)
  const destination = findDestination(tenant, getRouterParam(event, 'id'))
  const input = parseBody(z.object({ from: z.string().regex(/^\d{4}-\d{2}-\d{2}$/), to: z.string().regex(/^\d{4}-\d{2}-\d{2}$/) }), body)
  const form = formOf(tenant, destination.form_id)
  if (!form) throw new MockError('FRM-GEN-1004')
  const current = backfillState(destination)
  if (current?.status === 'running') throw new MockError('FRM-DEST-1017')
  const from = Date.parse(`${input.from}T00:00:00Z`)
  const to = Math.min(Date.parse(`${input.to}T23:59:59Z`), Date.parse(destination.covers_from))
  const total = deliveriesOf(tenant, destination, form).filter(delivery => delivery.status === 'not_sent' && Date.parse(delivery.submitted_at) >= from && Date.parse(delivery.submitted_at) <= to).length
  const now = Date.now()
  destination.backfill = { id: crypto.randomUUID(), from: new Date(from).toISOString(), to: new Date(to).toISOString(), total, done: 0, status: 'running', started_at: new Date(now).toISOString(), finished_at: null, started: now, speed: Math.max(20, total / 8) }
  saveDestinations()
  recordAudit(event, tenant, { action: 'data.backfill_started', actor: actorOf(user), resource: resource(tenant, destination), metadata: { from: input.from, to: input.to, count: String(total) } })
  return ok(detailOfDestination(tenant, destination), {}, 201)
})

/** For the connection panel: forms storing their responses on it (delete is refused while any do). */
export function formsOnConnection(tenant: MockTenant, datasourceId: string) {
  return destinationsOf(tenant)
    .filter(item => item.datasource_id === datasourceId)
    .map(item => ({ id: item.form_id, name: formOf(tenant, item.form_id)?.name ?? '' }))
}


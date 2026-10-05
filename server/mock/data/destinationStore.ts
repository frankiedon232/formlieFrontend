/**
 * Mock response storage (F12 M2). A destination sends one form's responses to a table on a
 * connection. Delivery status is worked out per response when read, from simple rules, so every
 * response (sample or real, old or new) has one without a queue to keep in step:
 *
 *   before the destination covers it            not sent (a backfill sends them)
 *   destination paused, after the pause         held
 *   connection failing / disabled since then     failed, retried with growing waits
 *   a few seconds old                            pending
 *   otherwise                                    sent
 *
 * Retries and backfills are recorded on top. Seeded workspaces start with two: a table Formalie
 * created on "Case management" (all sent) and an existing table on "Website leads" (failing for
 * the last hours, like its connection). Persisted across dev reloads.
 */
import type { BackfillJob, ColumnSource, Delivery, DeliveryStatus, DestinationColumn, DestinationDetail, DestinationRow, DestinationSettings, DestinationStatus } from '#shared/types/destinations'
import { allFields } from '#shared/utils/forms/build'
import { isInputField } from '#shared/utils/forms/fields'
import { columnNameFor, columnTypeFor, columnsForForm, matchColumns, standardSettings, tableNameFor, typedForEngine } from '#shared/utils/datasources/tables'
import { tablesSchemaOf } from '#shared/utils/datasources/permissions'
import { loadPersisted, savePersisted } from '../core/persist'
import { tablesOf, type CreatedTable } from './databaseTables'
import { seedOf, uuidFrom } from './dataSourceSim'
import { dataSourcesOf, statusOf, type StoredDataSource } from './dataSourceStore'
import { formsOf, type StoredForm } from './formStore'
import { formResponses, responseSchema, type IndexedResponse } from './responseData'
import { MOCK_USERS, SEEDED_TENANT_IDS, type MockTenant } from './tenants'

export interface DeliveryOverride {
  status: 'pending' | 'sent' | 'failed'
  attempts: number
  retry_at: number
  error_code: string | null
}

export interface StoredDestination {
  id: string
  form_id: string
  datasource_id: string
  table: { schema: string; name: string; created: boolean }
  columns: DestinationColumn[]
  settings: DestinationSettings
  paused_at: string | null
  covers_from: string
  backfill: (BackfillJob & { started: number; speed: number }) | null
  overrides: Record<string, DeliveryOverride>
  created_by: { id: string; name: string }
  created_at: string
  updated_at: string
}

const DAY = 86_400_000
const PENDING_MS = 4000
const stores = new Map<string, StoredDestination[]>(Object.entries(loadPersisted<Record<string, StoredDestination[]>>('destinations', {})))
export const saveDestinations = () => savePersisted('destinations', () => Object.fromEntries(stores))
const dayKey = (time: number) => new Date(time).toISOString().slice(0, 10)

/** The form's answer fields (what gets a column). */
export function inputFieldsOf(form: StoredForm) {
  const schema = responseSchema(form)
  return schema ? allFields(schema).filter(field => isInputField(field.type) && field.key) : []
}

export const DEFAULT_SETTINGS: DestinationSettings = { write_mode: 'insert', key_column: 'response_id', multi_value: 'json', choices: 'value' }

function seed(tenant: MockTenant): StoredDestination[] {
  const sources = dataSourcesOf(tenant)
  const cases = sources.find(source => source.id === uuidFrom(`${tenant.id}:datasource:1`))
  const leads = sources.find(source => source.id === uuidFrom(`${tenant.id}:datasource:4`))
  const forms = formsOf(tenant).forms.filter(form => !form.deleted_at && form.status === 'published' && inputFieldsOf(form).length)
  const onboarding = forms.find(form => /onboard/i.test(form.name)) ?? forms[0]
  const contact = forms.find(form => /contact|enquir|lead/i.test(form.name) && form !== onboarding) ?? forms.find(form => form !== onboarding)
  const owner = MOCK_USERS.find(user => user.tenant_id === tenant.id && user.role === 'owner') ?? MOCK_USERS[0]!
  const by = { id: owner.id, name: `${owner.first_name} ${owner.last_name}` }
  const list: StoredDestination[] = []
  const now = Date.now()
  if (cases && onboarding) {
    const created = new Date(now - 20 * DAY).toISOString()
    const fields = inputFieldsOf(onboarding)
    list.push({
      id: uuidFrom(`${tenant.id}:destination:1`),
      form_id: onboarding.id,
      datasource_id: cases.id,
      table: { schema: tablesSchemaOf(cases.engine, cases.settings, cases.access), name: tableNameFor(cases.engine, cases.access.table_prefix, onboarding.name), created: true },
      columns: columnsForForm(cases.engine, fields, DEFAULT_SETTINGS),
      settings: { ...DEFAULT_SETTINGS },
      paused_at: null,
      covers_from: created,
      backfill: null,
      overrides: {},
      created_by: by,
      created_at: created,
      updated_at: created,
    })
  }
  if (leads && contact) {
    const created = new Date(now - 18 * DAY).toISOString()
    const table = tablesOf(leads, []).find(item => item.name === 'leads')
    if (table) {
      list.push({
        id: uuidFrom(`${tenant.id}:destination:2`),
        form_id: contact.id,
        datasource_id: leads.id,
        table: { schema: table.schema, name: table.name, created: false },
        columns: matchColumns(table.columns, inputFieldsOf(contact)),
        settings: { ...DEFAULT_SETTINGS, key_column: 'submission_id', multi_value: 'text', choices: 'label' },
        paused_at: null,
        covers_from: created,
        backfill: null,
        overrides: {},
        created_by: by,
        created_at: created,
        updated_at: created,
      })
    }
  }
  return list
}

export function destinationsOf(tenant: MockTenant): StoredDestination[] {
  let list = stores.get(tenant.id)
  if (!list) {
    list = SEEDED_TENANT_IDS.has(tenant.id) ? seed(tenant) : []
    stores.set(tenant.id, list)
    saveDestinations()
  }
  // Tables Formalie created follow its standard (also those saved before it was set).
  for (const item of list) if (item.table.created && item.settings.write_mode !== 'upsert') item.settings = standardSettings(item.settings, item.columns)
  // Repair tables saved with another engine's types (before the server set them itself).
  for (const item of list) {
    if (!item.table.created) continue
    const source = dataSourcesOf(tenant).find(entry => entry.id === item.datasource_id)
    const form = formsOf(tenant).forms.find(entry => entry.id === item.form_id)
    if (!source || !form) continue
    const typed = typedForEngine(source.engine, item.columns, inputFieldsOf(form), item.settings.multi_value)
    if (typed.some((column, i) => column.type !== item.columns[i]!.type)) {
      item.columns = typed
      saveDestinations()
    }
  }
  return list
}

/** Response tables Formalie created on a connection (for the table lists). */
export function createdTablesOn(tenant: MockTenant, source: StoredDataSource): CreatedTable[] {
  return destinationsOf(tenant)
    .filter(item => item.datasource_id === source.id && item.table.created)
    .map(item => {
      const form = formsOf(tenant).forms.find(f => f.id === item.form_id)
      return { schema: item.table.schema, name: item.table.name, columns: item.columns, rows: form ? countSent(tenant, item, form) : 0 }
    })
}

/** Every form that stores in a database: form id → connection name and engine (cheap, for lists). */
export function storageMarks(tenant: MockTenant): Map<string, { mode: 'database'; datasource: string; engine: StoredDataSource['engine'] }> {
  const sources = new Map(dataSourcesOf(tenant).map(source => [source.id, source]))
  const marks = new Map<string, { mode: 'database'; datasource: string; engine: StoredDataSource['engine'] }>()
  for (const item of destinationsOf(tenant)) {
    const source = sources.get(item.datasource_id)
    if (source) marks.set(item.form_id, { mode: 'database', datasource: source.name, engine: source.engine })
  }
  return marks
}
export const FORMALIE_MARK = { mode: 'formalie' as const, datasource: null, engine: null }

// ── Delivery status ──────────────────────────────────────────────────────────────────────

interface Context {
  source: StoredDataSource | undefined
  coversFrom: number
  pausedAt: number | null
  failSince: number | null
  failCode: string | null
  backfill: { from: number; to: number; done: boolean } | null
  now: number
}

function contextOf(tenant: MockTenant, destination: StoredDestination): Context {
  const now = Date.now()
  const source = dataSourcesOf(tenant).find(item => item.id === destination.datasource_id)
  const status = source ? statusOf(source) : 'failing'
  const job = backfillState(destination, now)
  let coversFrom = Date.parse(destination.covers_from)
  if (job?.status === 'done') coversFrom = Math.min(coversFrom, Date.parse(job.from))
  const failing = !source || status === 'failing' || status === 'disabled'
  const since = failing ? (status === 'disabled' ? Date.parse(source!.updated_at) : Date.parse(source?.last_test?.finished_at ?? destination.created_at)) : null
  return {
    source,
    coversFrom,
    pausedAt: destination.paused_at ? Date.parse(destination.paused_at) : null,
    failSince: since,
    failCode: !source ? 'FRM-DEST-1001' : status === 'disabled' ? 'FRM-DEST-1009' : (source.last_test?.steps.find(step => step.error_code)?.error_code ?? 'FRM-DEST-1001'),
    backfill: job ? { from: Date.parse(job.from), to: Date.parse(job.to), done: job.status === 'done' } : null,
    now,
  }
}

const BACKOFF = [60_000, 300_000, 900_000, 3_600_000, 6 * 3_600_000]

function statusFor(entry: IndexedResponse, destination: StoredDestination, ctx: Context): Omit<Delivery, 'number' | 'submitted_at' | 'respondent' | 'response_id'> {
  const override = destination.overrides[entry.id]
  if (override) {
    if (override.status !== 'pending' || ctx.now < override.retry_at) return { status: override.status, attempts: override.attempts, error_code: override.error_code, at: new Date(override.retry_at).toISOString(), next_retry_at: override.status === 'pending' ? new Date(override.retry_at).toISOString() : null }
    if (ctx.failSince === null) return { status: 'sent', attempts: override.attempts + 1, error_code: null, at: new Date(override.retry_at).toISOString(), next_retry_at: null }
    return { status: 'failed', attempts: override.attempts + 1, error_code: ctx.failCode, at: new Date(override.retry_at).toISOString(), next_retry_at: new Date(override.retry_at + BACKOFF[Math.min(override.attempts, BACKOFF.length - 1)]!).toISOString() }
  }
  if (entry.at < ctx.coversFrom) {
    if (ctx.backfill && !ctx.backfill.done && entry.at >= ctx.backfill.from && entry.at <= ctx.backfill.to) return { status: 'pending', attempts: 0, error_code: null, at: null, next_retry_at: null }
    return { status: 'not_sent', attempts: 0, error_code: null, at: null, next_retry_at: null }
  }
  if (ctx.pausedAt !== null && entry.at >= ctx.pausedAt) return { status: 'held', attempts: 0, error_code: null, at: null, next_retry_at: null }
  if (ctx.failSince !== null && entry.at >= ctx.failSince - 10 * 60_000) {
    const waited = ctx.now - entry.at
    let attempts = 1
    let elapsed = 0
    while (attempts <= BACKOFF.length && elapsed + BACKOFF[attempts - 1]! <= waited) elapsed += BACKOFF[attempts++ - 1]!
    return { status: 'failed', attempts, error_code: ctx.failCode, at: new Date(entry.at + elapsed).toISOString(), next_retry_at: new Date(entry.at + elapsed + BACKOFF[Math.min(attempts - 1, BACKOFF.length - 1)]!).toISOString() }
  }
  if (ctx.now - entry.at < PENDING_MS) return { status: 'pending', attempts: 0, error_code: null, at: null, next_retry_at: new Date(entry.at + PENDING_MS).toISOString() }
  return { status: 'sent', attempts: 1, error_code: null, at: new Date(entry.at + 800 + (seedOf(entry.id) % 2200)).toISOString(), next_retry_at: null }
}

/** Every response of the form with its delivery, newest first. */
export function deliveriesOf(tenant: MockTenant, destination: StoredDestination, form: StoredForm): Delivery[] {
  const ctx = contextOf(tenant, destination)
  return formResponses(tenant, form)
    .slice()
    .sort((a, b) => b.at - a.at)
    .map(entry => ({ response_id: entry.id, number: entry.number, submitted_at: new Date(entry.at).toISOString(), respondent: entry.respondent.name || entry.respondent.email || null, ...statusFor(entry, destination, ctx) }))
}

function countSent(tenant: MockTenant, destination: StoredDestination, form: StoredForm): number {
  return deliveriesOf(tenant, destination, form).filter(delivery => delivery.status === 'sent').length
}

export function backfillState(destination: StoredDestination, now = Date.now()): BackfillJob | null {
  const job = destination.backfill
  if (!job) return null
  const done = Math.min(job.total, Math.floor(((now - job.started) / 1000) * job.speed))
  const finished = done >= job.total
  return { id: job.id, from: job.from, to: job.to, total: job.total, done, status: finished ? 'done' : 'running', started_at: job.started_at, finished_at: finished ? new Date(job.started + (job.total / job.speed) * 1000).toISOString() : null }
}

// ── Rows and detail ──────────────────────────────────────────────────────────────────────

export function statusOfDestination(destination: StoredDestination, deliveries: Delivery[], ctx?: Context): DestinationStatus {
  if (destination.paused_at) return 'paused'
  if (ctx?.failSince !== null && ctx?.failSince !== undefined) return 'failing'
  return deliveries.slice(0, 50).some(delivery => delivery.status === 'failed') ? 'failing' : 'active'
}

export function rowOfDestination(tenant: MockTenant, destination: StoredDestination): DestinationRow | null {
  const form = formsOf(tenant).forms.find(item => item.id === destination.form_id)
  const source = dataSourcesOf(tenant).find(item => item.id === destination.datasource_id)
  if (!form || !source) return null
  const ctx = contextOf(tenant, destination)
  const deliveries = deliveriesOf(tenant, destination, form)
  const now = Date.now()
  const daily = Array.from({ length: 30 }, (_, i) => ({ date: dayKey(now - (29 - i) * DAY), count: 0 }))
  let last: string | null = null
  for (const delivery of deliveries) {
    if (delivery.status !== 'sent' || !delivery.at) continue
    last ??= delivery.at
    const day = daily.find(item => item.date === delivery.at!.slice(0, 10))
    if (day) day.count++
  }
  const mapped = new Set(destination.columns.flatMap(column => (column.source?.kind === 'field' ? [column.source.key] : [])))
  return {
    id: destination.id,
    form: { id: form.id, name: form.name, status: form.status },
    datasource: { id: source.id, name: source.name, engine: source.engine, status: statusOf(source) },
    table: destination.table,
    status: statusOfDestination(destination, deliveries, ctx),
    settings: destination.settings,
    sent_30d: daily.reduce((sum, day) => sum + day.count, 0),
    pending: deliveries.filter(delivery => delivery.status === 'pending' || delivery.status === 'held').length,
    failed: deliveries.filter(delivery => delivery.status === 'failed').length,
    last_delivery_at: last,
    daily,
    new_fields: inputFieldsOf(form).filter(field => !mapped.has(field.key)).length,
    created_by: destination.created_by,
    created_at: destination.created_at,
    updated_at: destination.updated_at,
  }
}

export function detailOfDestination(tenant: MockTenant, destination: StoredDestination): DestinationDetail | null {
  const row = rowOfDestination(tenant, destination)
  const form = formsOf(tenant).forms.find(item => item.id === destination.form_id)
  const source = dataSourcesOf(tenant).find(item => item.id === destination.datasource_id)
  if (!row || !form || !source) return null
  const mapped = new Set(destination.columns.flatMap(column => (column.source?.kind === 'field' ? [column.source.key] : [])))
  const taken = new Set(destination.columns.map(column => column.column.toLowerCase()))
  const ctx = contextOf(tenant, destination)
  return {
    ...row,
    columns: destination.columns,
    fields: inputFieldsOf(form).map(field => ({ key: field.key, label: field.label ?? field.key })),
    unmapped_fields: inputFieldsOf(form)
      .filter(field => !mapped.has(field.key))
      .map(field => ({ key: field.key, label: field.label ?? field.key, column: columnNameFor(source.engine, field.key, taken), type: columnTypeFor(source.engine, field, destination.settings.multi_value) })),
    backfill: backfillState(destination),
    covers_from: new Date(ctx.coversFrom).toISOString(),
    not_sent: deliveriesOf(tenant, destination, form).filter(delivery => delivery.status === 'not_sent').length,
  }
}

export const sourceKey = (source: ColumnSource | null) => (source ? `${source.kind}:${source.key}` : '')
export type { DeliveryStatus }

/**
 * Mock Data sources API (F12 M1, docs/API-CONTRACT.md → Data sources). Admins only until Roles &
 * access (F22). Credentials are write-only: accepted on create / change, never in a reply.
 *
 *   GET    /datasources            list (q, sort, filter[status|engine|access])
 *   GET    /datasources/insights   the two chart cards
 *   GET    /datasources/meta       Formalie's outgoing addresses to allow
 *   POST   /datasources/test       start a test of a new or changed configuration → { id }
 *   GET    /datasources/tests/:id  the test so far (steps finish one after another)
 *   POST   /datasources            create (status from `test_id` when given)
 *   GET    /datasources/:id        detail (settings, which secrets are set, checks, uptime)
 *   PATCH  /datasources/:id        name, settings, access, secrets (only those sent), enabled
 *   POST   /datasources/:id/test   test the saved connection now → { id }
 *   POST   /datasources/:id/duplicate
 *   DELETE /datasources/:id        refused while forms send to it
 */
import { z } from 'zod'
import type { AuditChange } from '#shared/types/audit'
import { DATASOURCE_STATUSES, TABLE_PREFIXES, type ConnectionTest, type DataSourceConfig, type DataSourceInsights, type DataSourceSecrets } from '#shared/types/datasources'
import { addressOf, checkConfig, cleanSecrets, cleanSettings } from '#shared/utils/datasources/engines'
import { hasTablesSchema } from '#shared/utils/datasources/permissions'
import { DB_ENGINES } from '#shared/utils/integrations/databases'
import { actorOf, recordAudit } from '../core/audit'
import { requireAdmin } from '../core/auth'
import { MockError, ok, paginate } from '../core/respond'
import { defineMockRoute } from '../core/route'
import { parseBody } from '../core/validate'
import { finishedTest, planTest, testAt, type TestPlan } from '../data/dataSourceSim'
import { countOp, dataSourcesOf, detailOf, previousOps, rowOf, saveDataSources, statusOf, type StoredDataSource } from '../data/dataSourceStore'
import { platformEgressIps } from '../data/platformStore'
import type { MockTenant } from '../data/tenants'

const accessSchema = z.object({
  table_prefix: z.enum(TABLE_PREFIXES).default('formalie_'),
  tables_schema: z.string().trim().max(128).regex(/^$|^[\p{L}_][\p{L}\p{N}_$]*$/u).default(''),
  other: z.enum(['none', 'read', 'read_write']).default('read_write'),
  schemas: z.array(z.string().trim().min(1).max(128)).max(20).default([]),
})
const configSchema = z.object({
  engine: z.enum(DB_ENGINES as [string, ...string[]]),
  settings: z.record(z.string(), z.union([z.string().max(4000), z.number(), z.boolean()])),
  access: accessSchema,
  secrets: z.record(z.string(), z.string().max(20_000)).optional(),
})
const saveSchema = configSchema.extend({ name: z.string().trim().min(1).max(80), test_id: z.string().optional() })
const patchSchema = z.object({
  name: z.string().trim().min(1).max(80).optional(),
  settings: configSchema.shape.settings.optional(),
  access: accessSchema.optional(),
  secrets: configSchema.shape.secrets,
  enabled: z.boolean().optional(),
  test_id: z.string().optional(),
})

/** Field problems → FRM-GEN-1002 with per-field details (`settings.host`, `secrets.password`). */
function validate(config: DataSourceConfig, secrets: DataSourceSecrets, secretsSet: string[] = []) {
  const problems = checkConfig(config.engine, config.settings, secrets, secretsSet)
  const details = Object.entries(problems).map(([field, code]) => ({ field, message: code }))
  if (details.length) throw new MockError('FRM-GEN-1002', details)
}

function normalise(input: z.infer<typeof configSchema>): DataSourceConfig & { secrets: DataSourceSecrets } {
  const engine = input.engine as DataSourceConfig['engine']
  const settings = cleanSettings(engine, input.settings)
  // Only PostgreSQL and SQL Server put Formalie's tables in a schema chosen here.
  const access = { ...input.access, tables_schema: hasTablesSchema(engine) ? input.access.tables_schema : '' }
  return { engine, settings, access, secrets: cleanSecrets(engine, settings, input.secrets) }
}

function find(tenant: MockTenant, id: string | undefined): StoredDataSource {
  const source = dataSourcesOf(tenant).find(item => item.id === id)
  if (!source) throw new MockError('FRM-GEN-1004')
  return source
}

const nameTaken = (tenant: MockTenant, name: string, except?: string) => dataSourcesOf(tenant).some(item => item.id !== except && item.name.toLowerCase() === name.toLowerCase())
const resource = (source: StoredDataSource) => ({ type: 'data_source', id: source.id, name: source.name })

// ── Tests (in memory, 30 minutes) ────────────────────────────────────────────────────────

interface RunningTest {
  tenantId: string
  plan: TestPlan
  startedAt: number
  datasourceId: string | null
  label: string
  audited: boolean
}
const tests = new Map<string, RunningTest>()
const TEST_TTL = 30 * 60_000

function startTest(tenant: MockTenant, config: DataSourceConfig, secrets: DataSourceSecrets, datasourceId: string | null, label: string): string {
  for (const [id, test] of tests) if (Date.now() - test.startedAt > TEST_TTL) tests.delete(id)
  const id = crypto.randomUUID()
  tests.set(id, { tenantId: tenant.id, plan: planTest(config, secrets), startedAt: Date.now(), datasourceId, label, audited: false })
  return id
}

function testOf(tenant: MockTenant, id: string | undefined, finish = false): { run: RunningTest; test: ConnectionTest } {
  const run = id ? tests.get(id) : undefined
  if (!run || run.tenantId !== tenant.id) throw new MockError('FRM-DEST-1008')
  return { run, test: finish ? finishedTest(id!, run.plan, run.startedAt) : testAt(id!, run.plan, run.startedAt) }
}

export const startConnectionTest = defineMockRoute(({ event, body }) => {
  const { tenant } = requireAdmin(event)
  const input = parseBody(configSchema.extend({ datasource_id: z.string().optional() }), body)
  const saved = input.datasource_id ? find(tenant, input.datasource_id) : null
  const config = normalise(input)
  // Secrets left empty on a saved connection keep the stored ones.
  const secrets = { ...(saved && saved.engine === config.engine ? cleanSecrets(config.engine, config.settings, saved.secrets) : {}), ...config.secrets }
  validate(config, config.secrets, saved && saved.engine === config.engine ? Object.keys(secrets) : [])
  return ok({ id: startTest(tenant, config, secrets, saved?.id ?? null, saved?.name ?? addressOf(config.engine, config.settings)) }, {}, 201)
})

export const getConnectionTest = defineMockRoute(({ event }) => {
  const { tenant, user } = requireAdmin(event)
  const { run, test } = testOf(tenant, getRouterParam(event, 'id'))
  if (test.status !== 'running' && !run.audited) {
    run.audited = true
    const source = run.datasourceId ? dataSourcesOf(tenant).find(item => item.id === run.datasourceId) : null
    // "Test now" on a saved connection updates its status straight away.
    if (source) {
      source.last_test = test
      countOp(source)
      saveDataSources()
    }
    recordAudit(event, tenant, {
      action: 'data.connection_tested',
      actor: actorOf(user),
      outcome: test.status === 'failed' ? 'failure' : 'success',
      resource: source ? resource(source) : { type: 'data_source', id: null, name: run.label },
      metadata: { result: test.status, ...(test.steps.find(step => step.error_code) ? { code: test.steps.find(step => step.error_code)!.error_code! } : {}) },
    })
  }
  return ok(test)
})

/** POST /datasources/:id/test, test a saved connection with its stored settings. */
export const testSavedConnection = defineMockRoute(({ event }) => {
  const { tenant } = requireAdmin(event)
  const source = find(tenant, getRouterParam(event, 'id'))
  if (!source.enabled) throw new MockError('FRM-DEST-1009')
  return ok({ id: startTest(tenant, source, source.secrets, source.id, source.name) }, {}, 201)
})

// ── List, insights, meta ─────────────────────────────────────────────────────────────────

const inList = (value: unknown, actual: string) => typeof value !== 'string' || !value || value.split(',').includes(actual)

export const listDataSources = defineMockRoute(({ event, query }) => {
  const { tenant } = requireAdmin(event)
  const filter = (query.filter ?? {}) as Record<string, unknown>
  const rows = dataSourcesOf(tenant)
    .map(rowOf)
    .filter(row => inList(filter.status, row.status) && inList(filter.engine, row.engine) && inList(filter.access, row.access.other))
  const { data, meta } = paginate(rows, { sort: 'name', ...query }, (row, q) => [row.name, row.address, row.database, row.engine].some(text => text.toLowerCase().includes(q)))
  return ok(data, meta)
})

export const dataSourceInsights = defineMockRoute(({ event }) => {
  const { tenant } = requireAdmin(event)
  const sources = dataSourcesOf(tenant)
  const rows = sources.map(rowOf)
  const by_status = Object.fromEntries(DATASOURCE_STATUSES.map(status => [status, rows.filter(row => row.status === status).length])) as DataSourceInsights['by_status']
  const latencies = rows.filter(row => row.enabled && row.latency_ms !== null).map(row => row.latency_ms!)
  const daily = rows[0]?.daily.map((day, i) => ({ date: day.date, count: rows.reduce((sum, row) => sum + row.daily[i]!.count, 0) })) ?? []
  return ok<DataSourceInsights>({
    total: rows.length,
    by_status,
    forms_sending: rows.reduce((sum, row) => sum + row.forms_count, 0),
    operations_30d: rows.reduce((sum, row) => sum + row.operations_30d, 0),
    previous_30d: sources.reduce((sum, source) => sum + previousOps(source), 0),
    daily,
    avg_latency_ms: latencies.length ? Math.round(latencies.reduce((sum, value) => sum + value, 0) / latencies.length) : null,
    missing_permissions: rows.reduce((sum, row) => sum + row.missing_permissions, 0),
  })
})

export const dataSourceMeta = defineMockRoute(({ event }) => {
  requireAdmin(event)
  return ok({ egress_ips: platformEgressIps() })
})

// ── Create, read, change, duplicate, delete ──────────────────────────────────────────────

export const createDataSource = defineMockRoute(({ event, body }) => {
  const { tenant, user } = requireAdmin(event)
  const input = parseBody(saveSchema, body)
  const config = normalise(input)
  validate(config, config.secrets)
  if (nameTaken(tenant, input.name)) throw new MockError('FRM-DEST-1007', [{ field: 'name', message: 'taken' }])
  const now = new Date().toISOString()
  const source: StoredDataSource = {
    id: crypto.randomUUID(),
    name: input.name,
    engine: config.engine,
    settings: config.settings,
    secrets: config.secrets,
    access: config.access,
    enabled: true,
    last_test: input.test_id ? testOf(tenant, input.test_id, true).test : null,
    created_by: { id: user.id, name: `${user.first_name} ${user.last_name}`.trim() },
    created_at: now,
    updated_at: now,
    secrets_changed_at: now,
    ops: {},
    forms: [],
  }
  if (source.last_test) countOp(source)
  dataSourcesOf(tenant).push(source)
  saveDataSources()
  recordAudit(event, tenant, {
    action: 'data.connection_created',
    actor: actorOf(user),
    resource: resource(source),
    metadata: { engine: source.engine, address: addressOf(source.engine, source.settings), access: source.access.other, prefix: source.access.table_prefix, status: statusOf(source) },
  })
  return ok(detailOf(source), {}, 201)
})

export const getDataSource = defineMockRoute(({ event }) => {
  const { tenant } = requireAdmin(event)
  return ok(detailOf(find(tenant, getRouterParam(event, 'id'))))
})

export const patchDataSource = defineMockRoute(({ event, body }) => {
  const { tenant, user } = requireAdmin(event)
  const source = find(tenant, getRouterParam(event, 'id'))
  const input = parseBody(patchSchema, body)
  const changes: AuditChange[] = []
  const actor = actorOf(user)

  if (input.enabled !== undefined && input.enabled !== source.enabled) {
    source.enabled = input.enabled
    source.updated_at = new Date().toISOString()
    saveDataSources()
    recordAudit(event, tenant, { action: input.enabled ? 'data.connection_enabled' : 'data.connection_disabled', actor, resource: resource(source) })
    if (input.name === undefined && input.settings === undefined && input.access === undefined && !input.secrets) return ok(detailOf(source))
  }

  if (input.name !== undefined && input.name !== source.name) {
    if (nameTaken(tenant, input.name, source.id)) throw new MockError('FRM-DEST-1007', [{ field: 'name', message: 'taken' }])
    changes.push({ field: 'name', before: source.name, after: input.name })
    source.name = input.name
  }
  if (input.settings || input.access) {
    const config = normalise({ engine: source.engine, settings: input.settings ?? source.settings, access: input.access ?? source.access, secrets: input.secrets })
    const kept = cleanSecrets(config.engine, config.settings, source.secrets)
    validate(config, config.secrets, Object.keys(kept))
    const before = addressOf(source.engine, source.settings)
    const after = addressOf(config.engine, config.settings)
    if (before !== after) changes.push({ field: 'host', before, after })
    if (JSON.stringify(source.access) !== JSON.stringify(config.access)) changes.push({ field: 'access', before: source.access.other, after: config.access.other })
    if (JSON.stringify(source.settings) !== JSON.stringify(config.settings) && before === after) changes.push({ field: 'security', before: null, after: null })
    source.settings = config.settings
    source.access = config.access
    source.secrets = { ...kept, ...config.secrets }
    if (Object.keys(config.secrets).length) {
      source.secrets_changed_at = new Date().toISOString()
      recordAudit(event, tenant, { action: 'data.credentials_changed', actor, resource: resource(source), metadata: { fields: Object.keys(config.secrets).join(', ') } })
    }
  } else if (input.secrets && Object.keys(input.secrets).length) {
    const fresh = cleanSecrets(source.engine, source.settings, input.secrets)
    validate(source, fresh, Object.keys(source.secrets))
    source.secrets = { ...source.secrets, ...fresh }
    source.secrets_changed_at = new Date().toISOString()
    recordAudit(event, tenant, { action: 'data.credentials_changed', actor, resource: resource(source), metadata: { fields: Object.keys(fresh).join(', ') } })
  }
  // The test that was run for these changes becomes the connection's status.
  if (input.test_id) source.last_test = testOf(tenant, input.test_id, true).test
  else if (changes.some(change => change.field !== 'name')) source.last_test = null
  source.updated_at = new Date().toISOString()
  saveDataSources()
  if (changes.length) recordAudit(event, tenant, { action: 'data.connection_updated', actor, resource: resource(source), changes })
  return ok(detailOf(source))
})

export const duplicateDataSource = defineMockRoute(({ event }) => {
  const { tenant, user } = requireAdmin(event)
  const source = find(tenant, getRouterParam(event, 'id'))
  let name = `${source.name} (copy)`
  for (let n = 2; nameTaken(tenant, name); n++) name = `${source.name} (copy ${n})`
  const now = new Date().toISOString()
  const copy: StoredDataSource = {
    ...structuredClone(source),
    id: crypto.randomUUID(),
    name,
    last_test: null,
    created_by: { id: user.id, name: `${user.first_name} ${user.last_name}`.trim() },
    created_at: now,
    updated_at: now,
    ops: {},
    forms: [],
  }
  dataSourcesOf(tenant).push(copy)
  saveDataSources()
  recordAudit(event, tenant, { action: 'data.connection_duplicated', actor: actorOf(user), resource: resource(copy), metadata: { from: source.name } })
  return ok(detailOf(copy), {}, 201)
})

export const deleteDataSource = defineMockRoute(({ event }) => {
  const { tenant, user } = requireAdmin(event)
  const source = find(tenant, getRouterParam(event, 'id'))
  if (source.forms.length) throw new MockError('FRM-DEST-1010')
  const list = dataSourcesOf(tenant)
  list.splice(list.indexOf(source), 1)
  saveDataSources()
  recordAudit(event, tenant, { action: 'data.connection_deleted', actor: actorOf(user), resource: resource(source), metadata: { engine: source.engine, address: addressOf(source.engine, source.settings) } })
  return ok({ deleted: true })
})

/**
 * Mock data sources per workspace (F12 M1). Secrets stay here and are never put in a reply
 * (the real backend encrypts them at rest with a per-workspace key). Seeded workspaces start with
 * five connections that show every state: connected (read + write), connected (read only),
 * needs attention (a missing permission), failing (time-out) and disabled. Health checks every
 * five minutes are derived from the status, so the panel always has a recent history.
 * Persisted across dev reloads.
 */
import type { ConnectionTest, DataSourceAccessSettings, DataSourceCheck, DataSourceDetail, DataSourceRow, DataSourceSecrets, DataSourceSettings, DataSourceStatus, DbEngine } from '#shared/types/datasources'
import { addressOf, databaseNameOf, defaultSettings } from '#shared/utils/datasources/engines'
import { loadPersisted, savePersisted } from '../core/persist'
import { finishedTest, planTest, seedOf, uuidFrom } from './dataSourceSim'
import { MOCK_USERS, SEEDED_TENANT_IDS, type MockTenant } from './tenants'

export interface StoredDataSource {
  id: string
  name: string
  engine: DbEngine
  settings: DataSourceSettings
  secrets: DataSourceSecrets
  access: DataSourceAccessSettings
  enabled: boolean
  last_test: ConnectionTest | null
  created_by: { id: string; name: string }
  created_at: string
  updated_at: string
  secrets_changed_at: string | null
  /** Formalie operations per day (YYYY-MM-DD → count). */
  ops: Record<string, number>
  forms: { id: string; name: string }[]
}

const DAY = 86_400_000
const CHECK_EVERY = 5 * 60_000
const stores = new Map<string, StoredDataSource[]>(Object.entries(loadPersisted<Record<string, StoredDataSource[]>>('datasources', {})))
export const saveDataSources = () => savePersisted('datasources', () => Object.fromEntries(stores))

const dayKey = (time: number) => new Date(time).toISOString().slice(0, 10)
const PEM = '-----BEGIN CERTIFICATE-----\nMIIBmock\n-----END CERTIFICATE-----'

function seed(tenant: MockTenant): StoredDataSource[] {
  const owner = MOCK_USERS.find(user => user.tenant_id === tenant.id && user.role === 'owner') ?? MOCK_USERS[0]!
  const by = { id: owner.id, name: `${owner.first_name} ${owner.last_name}` }
  const now = Date.now()
  const make = (index: number, name: string, engine: DbEngine, settings: DataSourceSettings, secrets: DataSourceSecrets, access: DataSourceAccessSettings, extra: { ageDays: number; enabled?: boolean; fail?: { step: 'network'; code: string } }): StoredDataSource => {
    const id = uuidFrom(`${tenant.id}:datasource:${index}`)
    const merged = { ...defaultSettings(engine), ...settings }
    const created = now - extra.ageDays * DAY
    const plan = planTest({ engine, settings: merged, access }, secrets, { fail: extra.fail })
    const testId = uuidFrom(`${id}:test`)
    const ops: Record<string, number> = {}
    const level = access.mode === 'read_write' ? 900 : 300
    for (let day = 0; day < 60; day++) {
      const time = now - day * DAY
      if (time < created) break
      const weekday = new Date(time).getUTCDay()
      ops[dayKey(time)] = Math.round((level * (weekday === 0 || weekday === 6 ? 0.35 : 1) * (60 + (seedOf(`${id}${day}`) % 80))) / 100)
    }
    return {
      id,
      name,
      engine,
      settings: merged,
      secrets,
      access,
      enabled: extra.enabled ?? true,
      last_test: finishedTest(testId, plan, now - (extra.fail ? 3 : 1) * 3_600_000),
      created_by: by,
      created_at: new Date(created).toISOString(),
      updated_at: new Date(created + DAY).toISOString(),
      secrets_changed_at: new Date(created).toISOString(),
      ops,
      forms: [],
    }
  }
  return [
    make(1, 'Case management', 'postgresql', { host: 'cases-db.example.net', database: 'cases', schema: 'public', ssl_mode: 'verify-full', username: 'formalie_app' }, { password: 'mock', ca_certificate: PEM }, { mode: 'read_write', structure: true, schemas: ['public', 'intake'] }, { ageDays: 120 }),
    make(2, 'People records', 'sqlserver', { host: 'hr-sql.example.net', database: 'People', schema: 'dbo', username: 'formalie_reader' }, { password: 'mock' }, { mode: 'read_only', structure: false, schemas: [] }, { ageDays: 75 }),
    make(3, 'Finance warehouse', 'oracle', { host: 'fin-ora.example.net', port: 2484, service_name: 'FINPDB1', schema: 'FINANCE', username: 'formalie_limited' }, { password: 'mock' }, { mode: 'read_only', structure: false, schemas: [] }, { ageDays: 40 }),
    make(4, 'Website leads', 'mysql', { host: 'leads-db.example.net', database: 'leads', username: 'formalie_app' }, { password: 'mock' }, { mode: 'read_write', structure: false, schemas: [] }, { ageDays: 22, fail: { step: 'network', code: 'FRM-DEST-1011' } }),
    make(5, 'Legacy intake', 'mariadb', { host: 'legacy-db.example.net', database: 'intake_2019', username: 'formalie_app' }, { password: 'mock' }, { mode: 'read_only', structure: false, schemas: [] }, { ageDays: 300, enabled: false }),
  ]
}

export function dataSourcesOf(tenant: MockTenant): StoredDataSource[] {
  let list = stores.get(tenant.id)
  if (!list) {
    list = SEEDED_TENANT_IDS.has(tenant.id) ? seed(tenant) : []
    stores.set(tenant.id, list)
    saveDataSources()
  }
  return list
}

export function statusOf(source: StoredDataSource): DataSourceStatus {
  if (!source.enabled) return 'disabled'
  if (!source.last_test || source.last_test.status === 'running') return 'untested'
  return source.last_test.status === 'failed' ? 'failing' : source.last_test.status === 'warning' ? 'attention' : 'connected'
}

/** Health checks every five minutes since the last test (newest first), up to `count`. */
export function checksOf(source: StoredDataSource, count = 12): DataSourceCheck[] {
  const test = source.last_test
  if (!test?.finished_at || !source.enabled) return test?.finished_at ? [{ at: test.finished_at, status: test.status === 'failed' ? 'failed' : test.status === 'warning' ? 'warning' : 'passed', latency_ms: test.latency_ms, error_code: test.steps.find(step => step.error_code)?.error_code ?? null }] : []
  const since = Date.parse(test.finished_at)
  const latest = Math.floor(Date.now() / CHECK_EVERY) * CHECK_EVERY
  const checks: DataSourceCheck[] = []
  for (let at = latest; at >= since && checks.length < count; at -= CHECK_EVERY) {
    const jitter = seedOf(`${source.id}${at}`) % 9
    checks.push({
      at: new Date(at).toISOString(),
      status: test.status === 'failed' ? 'failed' : test.status === 'warning' ? 'warning' : 'passed',
      latency_ms: test.latency_ms === null ? null : test.latency_ms + jitter - 4,
      error_code: test.steps.find(step => step.error_code)?.error_code ?? null,
    })
  }
  if (!checks.length) checks.push({ at: test.finished_at, status: test.status === 'failed' ? 'failed' : test.status === 'warning' ? 'warning' : 'passed', latency_ms: test.latency_ms, error_code: null })
  return checks
}

function uptimeDaily(source: StoredDataSource): { date: string; uptime: number | null }[] {
  const now = Date.now()
  const created = Date.parse(source.created_at)
  const failingSince = source.last_test?.status === 'failed' && source.last_test.finished_at ? Date.parse(source.last_test.finished_at) : null
  return Array.from({ length: 30 }, (_, i) => {
    const time = now - (29 - i) * DAY
    const date = dayKey(time)
    if (time + DAY < created || !source.last_test || (!source.enabled && time > Date.parse(source.updated_at))) return { date, uptime: null }
    if (failingSince && time + DAY > failingSince) return { date, uptime: Math.max(0, Math.round(100 - ((now - Math.max(failingSince, time)) / DAY) * 100)) }
    const dip = seedOf(`${source.id}${date}`) % 23 === 0 ? 2 + (seedOf(date) % 6) : 0
    return { date, uptime: 100 - dip }
  })
}

export function rowOf(source: StoredDataSource): DataSourceRow {
  const now = Date.now()
  const daily = Array.from({ length: 30 }, (_, i) => {
    const date = dayKey(now - (29 - i) * DAY)
    return { date, count: source.ops[date] ?? 0 }
  })
  const days = uptimeDaily(source).filter(day => day.uptime !== null)
  const checks = checksOf(source, 1)
  return {
    id: source.id,
    name: source.name,
    engine: source.engine,
    address: addressOf(source.engine, source.settings),
    database: databaseNameOf(source.engine, source.settings),
    access: source.access,
    status: statusOf(source),
    enabled: source.enabled,
    server_version: source.last_test?.server_version ?? null,
    latency_ms: checks[0]?.latency_ms ?? null,
    last_checked_at: checks[0]?.at ?? null,
    uptime_30d: days.length ? Math.round((days.reduce((sum, day) => sum + day.uptime!, 0) / days.length) * 10) / 10 : null,
    operations_30d: daily.reduce((sum, day) => sum + day.count, 0),
    daily,
    forms_count: source.forms.length,
    missing_permissions: source.last_test?.permissions.filter(item => item.status === 'missing').length ?? 0,
    created_by: source.created_by,
    created_at: source.created_at,
    updated_at: source.updated_at,
  }
}

export function detailOf(source: StoredDataSource): DataSourceDetail {
  return {
    ...rowOf(source),
    settings: source.settings,
    secrets_set: Object.keys(source.secrets),
    secrets_changed_at: source.secrets_changed_at,
    last_test: source.last_test,
    checks: checksOf(source),
    uptime_daily: uptimeDaily(source),
    forms: source.forms,
  }
}

/** Operations in the 30 days before the last 30 (the change on the chart card). */
export function previousOps(source: StoredDataSource): number {
  const now = Date.now()
  let total = 0
  for (let day = 30; day < 60; day++) total += source.ops[dayKey(now - day * DAY)] ?? 0
  return total
}

export const countOp = (source: StoredDataSource) => {
  const key = dayKey(Date.now())
  source.ops[key] = (source.ops[key] ?? 0) + 1
}

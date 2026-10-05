/**
 * Mock connection tests (F12 M1). The real backend connects from its own servers, step by step,
 * and checks every permission through the catalogue (MySQL SHOW GRANTS, PostgreSQL
 * has_*_privilege, SQL Server fn_my_permissions, Oracle SESSION_PRIVS / ALL_TAB_PRIVS). A test never
 * changes data. Here the outcome is decided up front and revealed over time, so the UI shows real
 * progress. Dev triggers (docs/02-DEV-ENVIRONMENT.md → Data sources):
 *
 *   host contains "unreachable" → network fails (FRM-DEST-1001) · "timeout" → FRM-DEST-1011
 *   SSH host contains "unreachable" → tunnel fails (FRM-DEST-1004)
 *   host contains "badcert" → TLS fails (FRM-DEST-1003)
 *   password / client secret "wrong" → sign-in fails (FRM-DEST-1002)
 *   database / service name contains "missing" → FRM-DEST-1005
 *   user name contains "readonly" → no write or structure grants · "limited" → no row counts,
 *   no structure · root / sa / sys / system / postgres / "admin" → administrator account warning ·
 *   "writer" on a read-only connection → more rights than needed
 */
import { createHash } from 'node:crypto'
import { TEST_STEPS, type ConnectionTest, type DataSourceConfig, type DataSourceSecrets, type PermissionResult, type TestFinding, type TestStep, type TestStepKey } from '#shared/types/datasources'
import { databaseNameOf, defaultSchemaOf, isEncrypted } from '#shared/utils/datasources/engines'
import { operationsFor } from '#shared/utils/datasources/permissions'

/** A stable number from text (same input, same mock result). */
export const seedOf = (text: string) => createHash('sha256').update(text).digest().readUInt32BE(0)

/** A stable UUID from text (seeded records). */
export function uuidFrom(text: string): string {
  const hex = createHash('sha256').update(text).digest('hex')
  return `${hex.slice(0, 8)}-${hex.slice(8, 12)}-4${hex.slice(13, 16)}-a${hex.slice(17, 20)}-${hex.slice(20, 32)}`
}

const VERSIONS = { mysql: '8.4.2', mariadb: '11.4.3', postgresql: '16.4', sqlserver: '2022 (16.0.4135)', oracle: '23ai (23.5)' }
const STEP_MS: Record<TestStepKey, number> = { network: 500, ssh: 600, tls: 500, sign_in: 600, database: 500, permissions: 900 }

export interface TestPlan {
  steps: { key: TestStepKey; outcome: 'passed' | 'warning' | 'failed' | 'skipped'; error_code: string | null }[]
  result: Omit<ConnectionTest, 'id' | 'status' | 'started_at' | 'finished_at' | 'steps'>
}

const ADMIN = /^(root|sa|sys|system|postgres|dbadmin)$|admin/i

/** Decide what a test of this configuration finds. */
export function planTest(config: DataSourceConfig, secrets: DataSourceSecrets, options: { fail?: { step: TestStepKey; code: string } } = {}): TestPlan {
  const { engine, settings, access } = config
  const host = String(settings.host ?? settings.descriptor ?? '').toLowerCase()
  const user = String(settings.username ?? settings.client_id ?? '').toLowerCase()
  const encrypted = isEncrypted(engine, settings)

  let fail = options.fail ?? null
  const failWith = (step: TestStepKey, code: string) => (fail ??= { step, code })
  if (host.includes('unreachable')) failWith('network', 'FRM-DEST-1001')
  if (host.includes('timeout')) failWith('network', 'FRM-DEST-1011')
  if (settings.ssh && String(settings.ssh_host).toLowerCase().includes('unreachable')) failWith('ssh', 'FRM-DEST-1004')
  if (encrypted && host.includes('badcert')) failWith('tls', 'FRM-DEST-1003')
  if (secrets.password === 'wrong' || secrets.client_secret === 'wrong') failWith('sign_in', 'FRM-DEST-1002')
  if (databaseNameOf(engine, settings).toLowerCase().includes('missing')) failWith('database', 'FRM-DEST-1005')

  const missing = new Set<string>()
  if (user.includes('readonly')) ['insert', 'update', 'delete', 'sequences', 'create_table', 'alter_table', 'create_index'].forEach(key => missing.add(key))
  if (user.includes('limited')) ['row_counts', 'create_table', 'alter_table', 'create_index'].forEach(key => missing.add(key))
  const permissions: PermissionResult[] = operationsFor(engine, access).map(operation => ({
    operation: operation.key,
    status: !operation.needed ? 'not_needed' : missing.has(operation.key) ? 'missing' : 'granted',
  }))

  const findings: TestFinding[] = []
  if (permissions.some(item => item.status === 'missing')) findings.push('missing_permissions')
  if (ADMIN.test(user)) findings.push('admin_account')
  if (access.mode === 'read_only' && user.includes('writer')) findings.push('extra_write')
  if (!encrypted) findings.push('tls_off')
  if (engine === 'sqlserver' && settings.trust_server_certificate) findings.push('trust_certificate')

  let failed = false
  const steps: TestPlan['steps'] = TEST_STEPS.map(key => {
    if (failed) return { key, outcome: 'skipped', error_code: null }
    if (fail?.step === key) {
      failed = true
      return { key, outcome: 'failed', error_code: fail.code }
    }
    if (key === 'ssh' && !settings.ssh) return { key, outcome: 'skipped', error_code: null }
    if (key === 'tls' && !encrypted) return { key, outcome: 'warning', error_code: null }
    if (key === 'permissions' && findings.includes('missing_permissions')) return { key, outcome: 'warning', error_code: 'FRM-DEST-1006' }
    return { key, outcome: 'passed', error_code: null }
  })

  const seed = seedOf(`${engine}|${host}|${user}`)
  const schema = defaultSchemaOf(engine, settings) || 'public'
  const schemas = [...new Set([schema, ...access.schemas, engine === 'oracle' ? 'REPORTING' : 'reporting'])]
  return {
    steps,
    result: {
      server_version: failed && steps.findIndex(step => step.outcome === 'failed') < 3 ? null : VERSIONS[engine],
      latency_ms: steps[0]!.outcome === 'failed' ? null : 12 + (seed % 48),
      permissions: failed ? [] : permissions,
      findings: failed ? [] : findings,
      schemas: failed ? [] : schemas,
      tables_count: failed ? null : 12 + (seed % 37),
    },
  }
}

/** The test as it stands `elapsed` ms after it started (steps finish one after another). */
export function testAt(id: string, plan: TestPlan, startedAt: number, now = Date.now()): ConnectionTest {
  let clock = startedAt
  let running = false
  const steps: TestStep[] = plan.steps.map(step => {
    if (step.outcome === 'skipped') return { key: step.key, status: running ? 'pending' : 'skipped', duration_ms: null, error_code: null }
    const ms = STEP_MS[step.key] + (seedOf(id + step.key) % 250)
    if (running) return { key: step.key, status: 'pending', duration_ms: null, error_code: null }
    if (now < clock + ms) {
      running = true
      return { key: step.key, status: 'running', duration_ms: null, error_code: null }
    }
    clock += ms
    return { key: step.key, status: step.outcome, duration_ms: ms, error_code: step.error_code }
  })
  const done = !running
  const status = !done ? 'running' : steps.some(step => step.status === 'failed') ? 'failed' : steps.some(step => step.status === 'warning' && step.key === 'permissions') || plan.result.findings.some(finding => finding !== 'trust_certificate') ? 'warning' : 'passed'
  return {
    id,
    status,
    started_at: new Date(startedAt).toISOString(),
    finished_at: done ? new Date(clock).toISOString() : null,
    steps,
    ...(done ? plan.result : { server_version: null, latency_ms: null, permissions: [], findings: [], schemas: [], tables_count: null }),
  }
}

/** The finished result straight away (seeding, or saving before the poll caught up). */
export const finishedTest = (id: string, plan: TestPlan, startedAt: number) => testAt(id, plan, startedAt, Number.MAX_SAFE_INTEGER)

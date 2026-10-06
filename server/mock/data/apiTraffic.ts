/**
 * API traffic in the mock (F13 M4): the request log and what analytics are built from. Real calls to
 * the mock public API are kept in `.data/mock/api-logs.json` (newest 2,000 per workspace); a sample
 * history of the last 7 days is made up on the fly from each endpoint's daily call numbers, stable
 * per endpoint and day, so the log is never empty. The token itself is never logged.
 */
import { createHash } from 'node:crypto'
import type { ApiLogEntry, ApiTokenMode } from '#shared/types/apiService'
import { loadPersisted, savePersisted } from '../core/persist'
import { scopeAllows } from '#shared/utils/apiService/tokens'
import { apiOf, endpointUsage, type StoredApiEndpoint } from './apiStore'
import { seedOf } from './dataSourceSim'
import type { MockTenant } from './tenants'

export interface StoredLog extends ApiLogEntry {
  request_body: unknown | null
  response_body: unknown | null
  request_headers: Record<string, string>
}

const DAY = 86_400_000
const SAMPLE_DAYS = 7
const KEEP = 2000
const stores = new Map<string, StoredLog[]>(Object.entries(loadPersisted<Record<string, StoredLog[]>>('api-logs', {})))
let saveTimer: ReturnType<typeof setTimeout> | null = null
/** Saved a moment later, so a burst of calls writes the file once. */
const saveLogs = () => {
  if (saveTimer) return
  saveTimer = setTimeout(() => {
    saveTimer = null
    savePersisted('api-logs', () => Object.fromEntries(stores))
  }, 500)
}
export const realLogsOf = (tenant: MockTenant) => stores.get(tenant.id) ?? []

export function recordLog(tenant: MockTenant, entry: StoredLog) {
  const list = stores.get(tenant.id) ?? []
  list.unshift(entry)
  if (list.length > KEEP) list.length = KEEP
  stores.set(tenant.id, list)
  saveLogs()
}

const uuidOf = (text: string) => {
  const hex = createHash('sha256').update(text).digest('hex')
  return `${hex.slice(0, 8)}-${hex.slice(8, 12)}-4${hex.slice(13, 16)}-a${hex.slice(17, 20)}-${hex.slice(20, 32)}`
}
const COUNTRIES = ['GB', 'US', 'NG', 'DE', 'IN', 'BR', 'KE', 'FR', 'JP', 'ZA', 'CA', 'AU', 'NL', 'SG', 'AE', 'MX', 'ID', 'EG']
const AGENTS = ['PostmanRuntime/7.39.0', 'python-requests/2.32.3', 'axios/1.7.7', 'okhttp/4.12.0', 'curl/8.7.1', 'Go-http-client/2.0']
const ERRORS: { status: number; code: string }[] = [
  { status: 422, code: 'FRM-RESP-1001' },
  { status: 401, code: 'FRM-API-1010' },
  { status: 429, code: 'FRM-GEN-1029' },
  { status: 403, code: 'FRM-API-1015' },
  { status: 404, code: 'FRM-API-1013' },
  { status: 500, code: 'FRM-GEN-5000' },
]

/** Made-up calls of one endpoint on one day (at most 12, from its daily count; never in the future). */
function sampleDay(tenant: MockTenant, endpoint: StoredApiEndpoint, date: string, count: number, errorShare: number, avgMs: number): StoredLog[] {
  const api = apiOf(tenant)
  const service = api.services.find(item => item.id === endpoint.service_id)
  const tokens = api.tokens.filter(token => token.revoked_at === null)
  const out: StoredLog[] = []
  const start = Date.parse(date)
  for (let i = 0; i < Math.min(12, count); i++) {
    const seed = (part: string) => seedOf(`${endpoint.id}:${date}:${i}:${part}`)
    const at = start + (seed('t') % DAY)
    if (at > Date.now()) continue
    const method = endpoint.methods[seed('m') % endpoint.methods.length] ?? 'POST'
    const failed = (seed('e') % 1000) / 1000 < errorShare
    const error = ERRORS[seed('c') % ERRORS.length]!
    const status = failed ? error.status : method === 'POST' ? 201 : 200
    // Only tokens that may make this call (their scopes), and never one with no valid token
    const allowed = tokens.filter(item => scopeAllows(item.scopes, { endpoint_id: endpoint.id, service_id: endpoint.service_id, method }))
    const token = failed && error.code === 'FRM-API-1010' ? null : (allowed[seed('k') % Math.max(1, allowed.length)] ?? null)
    const one = method !== 'POST' && seed('o') % 3 === 0
    const v6 = seed('6') % 5 === 0
    out.push({
      id: uuidOf(`log:${endpoint.id}:${date}:${i}`),
      at: new Date(at).toISOString(),
      method,
      path: `/${api.api_key}/${endpoint.name}${one || method === 'PUT' || method === 'DELETE' ? '/rsp_' + (seed('r') % 100000).toString(36) : ''}`,
      status,
      code: failed ? error.code : null,
      duration_ms: Math.max(8, Math.round(avgMs * (0.4 + (seed('d') % 220) / 100))),
      endpoint: { id: endpoint.id, name: endpoint.name },
      service: service ? { id: service.id, name: service.name } : null,
      token: token ? { id: token.id, name: token.name, mode: token.mode as ApiTokenMode } : null,
      ip: v6 ? `2001:db8::${(seed('i') % 65535).toString(16)}` : `${seed('n') % 2 ? '203.0.113' : '198.51.100'}.${(seed('i') % 250) + 2}`,
      country: COUNTRIES[seed('g') % COUNTRIES.length]!,
      user_agent: AGENTS[seed('u') % AGENTS.length]!,
      request_id: uuidOf(`req:${endpoint.id}:${date}:${i}`),
      request_body: null,
      response_body: null,
      request_headers: {},
    })
  }
  return out
}

/** Every log entry in a time window (sample history of the last 7 days + real calls), newest first. */
export function logsOf(tenant: MockTenant, from = Date.now() - SAMPLE_DAYS * DAY, to = Date.now()): StoredLog[] {
  const api = apiOf(tenant)
  const sample: StoredLog[] = []
  for (const endpoint of api.endpoints) {
    const usage = endpointUsage(tenant, endpoint)
    const share = usage.calls_30d ? usage.errors_30d / usage.calls_30d : 0
    for (const day of usage.daily.slice(-SAMPLE_DAYS)) sample.push(...sampleDay(tenant, endpoint, day.date, day.count, share, usage.avg_ms ?? 80))
  }
  return [...realLogsOf(tenant), ...sample].filter(item => {
    const at = Date.parse(item.at)
    return at >= from && at <= to
  }).sort((a, b) => b.at.localeCompare(a.at))
}

/** One entry by id (real, or regenerated from the sample history). */
export const logById = (tenant: MockTenant, id: string) => logsOf(tenant, 0).find(item => item.id === id) ?? null

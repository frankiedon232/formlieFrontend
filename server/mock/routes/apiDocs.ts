/**
 * Mock Docs console (F13 M5): `POST /api-endpoints/:id/try` sends one call through the mock public API
 * with a test token that lives a minute (every check runs: access rules, limits, required headers,
 * the form's rules; nothing is stored). Admins only until F22.
 */
import { z } from 'zod'
import type { ApiTryResult } from '#shared/types/apiService'
import { API_METHODS } from '#shared/utils/urls/public'
import { encodeId } from '../core/ids'
import { requireAdmin } from '../core/auth'
import { MockError, ok } from '../core/respond'
import { defineMockRoute } from '../core/route'
import { parseBody } from '../core/validate'
import { apiOf } from '../data/apiStore'
import { issueConsoleToken } from '../publicApi'

const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i
const SHOWN = ['x-request-id', 'x-ratelimit-limit', 'x-ratelimit-remaining', 'retry-after', 'content-type', 'formalie-token-expires']

export const tryEndpoint = defineMockRoute(async ({ event, body }) => {
  const { tenant } = requireAdmin(event)
  const values = parseBody(z.object({ method: z.enum(API_METHODS), record_id: z.string().trim().max(100).nullish(), body: z.unknown().optional(), headers: z.record(z.string().max(64), z.string().max(500)).optional() }), body)
  const api = apiOf(tenant)
  const endpoint = api.endpoints.find(item => item.id === getRouterParam(event, 'id'))
  if (!endpoint) throw new MockError('FRM-GEN-1004')
  // The portal turns references into ids on the way in; the public API expects the reference again
  const record = values.record_id ? (UUID.test(values.record_id) ? encodeId(values.record_id) : values.record_id) : ''
  const headers: Record<string, string> = { ...(values.headers ?? {}), authorization: `Bearer ${issueConsoleToken(tenant.id)}` }
  const writes = values.method === 'POST' || values.method === 'PUT'
  // The three headers every call sends: Content-Type (always) and a Formalie-Key when the console did not give one
  headers['content-type'] = 'application/json'
  if (!Object.keys(headers).some(name => name.toLowerCase() === 'formalie-key')) headers['formalie-key'] = crypto.randomUUID()
  const started = Date.now()
  const response = await $fetch.raw(`/public-api/${api.api_key}/${endpoint.name}${record ? `/${encodeURIComponent(record)}` : ''}`, {
    method: values.method,
    headers,
    body: writes ? JSON.stringify(values.body ?? {}) : undefined,
    ignoreResponseError: true,
  })
  const result: ApiTryResult = {
    status: response.status,
    duration_ms: Date.now() - started,
    headers: Object.fromEntries(SHOWN.map(name => [name, response.headers.get(name)]).filter((entry): entry is [string, string] => !!entry[1])),
    body: response._data ?? null,
  }
  return ok(result)
})

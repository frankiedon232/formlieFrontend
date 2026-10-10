/**
 * Requests to the Formalie support team (F25, owner 2026-10-10): "Contact support" in Help & support opens a form
 * inside the app; what is sent goes to the Formalie team, who answer it in the platform admin (replies by email).
 * Kept in `.data/mock/support.json` (platform-wide, with the workspace and person it came from). Any signed-in member.
 *
 *   GET  /help/support-requests     the person's own requests in this workspace (newest first)
 *   POST /help/support-requests     SupportRequestInput → SupportRequest (with a reference such as SR-48213)
 */
import { z } from 'zod'
import { HELP_CATEGORIES, SUPPORT_TOPICS, type SupportRequest } from '#shared/types/help'
import { requireAuth } from '../core/auth'
import { MockError, ok } from '../core/respond'
import { defineMockRoute } from '../core/route'
import { loadPersisted, savePersisted } from '../core/persist'
import { parseBody } from '../core/validate'

interface StoredRequest extends SupportRequest {
  tenant_id: string
  workspace: string
  user_id: string
  name: string
}
const requests: StoredRequest[] = loadPersisted<StoredRequest[]>('support', [])
const save = () => savePersisted('support', () => requests)

const schema = z.object({
  topic: z.enum(SUPPORT_TOPICS),
  area: z.enum(HELP_CATEGORIES).nullable(),
  subject: z.string().trim().min(3).max(140),
  message: z.string().trim().min(10).max(5000),
  urgent: z.boolean(),
  email: z.string().trim().toLowerCase().pipe(z.email()),
  page: z.string().trim().max(300).nullable(),
  article: z.string().trim().max(120).nullable(),
})
const strip = ({ tenant_id: _t, workspace: _w, user_id: _u, name: _n, ...request }: StoredRequest): SupportRequest => request

export const listSupportRequests = defineMockRoute(({ event }) => {
  const { tenant, user } = requireAuth(event)
  return ok(requests.filter(item => item.tenant_id === tenant.id && item.user_id === user.id).slice(0, 20).map(strip))
})

export const sendSupportRequest = defineMockRoute(({ event, body }) => {
  const { tenant, user } = requireAuth(event)
  const input = parseBody(schema, body)
  // The same subject again within a minute is a double send
  if (requests.some(item => item.user_id === user.id && item.subject === input.subject && Date.now() - Date.parse(item.created_at) < 60_000)) throw new MockError('FRM-HELP-1001')
  let reference = ''
  do reference = `SR-${Math.floor(10_000 + Math.random() * 90_000)}`
  while (requests.some(item => item.reference === reference))
  const request: StoredRequest = { ...input, id: crypto.randomUUID(), reference, status: 'open', created_at: new Date().toISOString(), tenant_id: tenant.id, workspace: tenant.subdomain, user_id: user.id, name: `${user.first_name} ${user.last_name}`.trim() }
  requests.unshift(request)
  save()
  return ok(strip(request))
})

/**
 * Workspace address (F14 M7, docs/API-CONTRACT.md → Settings). Admins only. Own domains are not
 * offered (owner, 2026-10-07).
 *
 *   GET  /settings/address              subdomain, portal address, old addresses
 *   POST /settings/address/subdomain    { subdomain, confirm } (confirm = the new subdomain again)
 *
 * The old subdomain keeps leading here for 90 days. Every change is in the audit trail.
 */
import type { H3Event } from 'h3'
import { z } from 'zod'
import type { WorkspaceAddress } from '#shared/types/address'
import { isValidSubdomain } from '#shared/utils/tenant/host'
import { actorOf, recordAudit } from '../core/audit'
import { requireAdmin } from '../core/auth'
import { MockError, ok } from '../core/respond'
import { defineMockRoute } from '../core/route'
import { parseBody } from '../core/validate'
import { addressOf, changeSubdomain, subdomainTaken } from '../data/addressStore'
import type { MockTenant, MockUser } from '../data/tenants'

function view(event: H3Event, tenant: MockTenant): WorkspaceAddress {
  const address = addressOf(tenant)
  const root = useRuntimeConfig(event).public.rootDomain
  const now = Date.now()
  return { subdomain: tenant.subdomain, url: `https://${tenant.subdomain}.${root}`, previous: address.previous.filter(item => Date.parse(item.until) > now) }
}
const audit = (event: H3Event, tenant: MockTenant, user: MockUser, field: string, before: string | null, after: string | null) =>
  recordAudit(event, tenant, { action: 'settings.updated', actor: actorOf(user), resource: { type: 'setting', id: null, name: 'Address and domain' }, changes: [{ field, before, after }] })

export const getAddress = defineMockRoute(({ event }) => {
  const { tenant } = requireAdmin(event)
  return ok(view(event, tenant))
})

const subdomainSchema = z.object({ subdomain: z.string().trim().toLowerCase().min(3).max(63), confirm: z.string().trim().toLowerCase() })

export const changeWorkspaceSubdomain = defineMockRoute(({ event, body }) => {
  const { tenant, user } = requireAdmin(event)
  const input = parseBody(subdomainSchema, body)
  if (input.confirm !== input.subdomain) throw new MockError('FRM-GEN-1002', [{ field: 'confirm', message: 'confirm' }])
  if (input.subdomain === tenant.subdomain) return ok(view(event, tenant))
  // Its own old address may come back; anything else in use is taken
  const ownOld = addressOf(tenant).previous.some(item => item.subdomain === input.subdomain)
  if (!isValidSubdomain(input.subdomain) || (!ownOld && subdomainTaken(input.subdomain))) throw new MockError('FRM-TEN-1004', [{ field: 'subdomain', message: isValidSubdomain(input.subdomain) ? 'taken' : 'invalid' }])
  const before = tenant.subdomain
  changeSubdomain(tenant, input.subdomain)
  audit(event, tenant, user, 'subdomain', before, input.subdomain)
  return ok(view(event, tenant))
})

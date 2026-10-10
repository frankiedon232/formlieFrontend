/**
 * Workspace address and own domain (F14 M7, docs/API-CONTRACT.md → Settings). Admins only.
 *
 *   GET    /settings/address                     subdomain, portal address, old addresses, own domain
 *   POST   /settings/address/subdomain           { subdomain, confirm } (confirm = the new subdomain again)
 *   PUT    /settings/address/domain              { domain } → the DNS records to add
 *   POST   /settings/address/domain/check        looks the records up in DNS (really) → status
 *   DELETE /settings/address/domain
 *
 * The old subdomain keeps leading here for 90 days. Every change is in the audit trail.
 */
import { requireFeature } from '../core/plan'
import { resolveCname, resolveTxt } from 'node:dns/promises'
import type { H3Event } from 'h3'
import { z } from 'zod'
import type { CustomDomain, WorkspaceAddress } from '#shared/types/address'
import { isValidSubdomain } from '#shared/utils/tenant/host'
import { actorOf, recordAudit } from '../core/audit'
import { requireAdmin } from '../core/auth'
import { MockError, ok } from '../core/respond'
import { defineMockRoute } from '../core/route'
import { parseBody } from '../core/validate'
import { addressOf, changeSubdomain, setDomain, subdomainTaken } from '../data/addressStore'
import type { MockTenant, MockUser } from '../data/tenants'

const DOMAIN = /^(?=.{4,253}$)([a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,63}$/

function view(event: H3Event, tenant: MockTenant): WorkspaceAddress {
  const address = addressOf(tenant)
  const root = useRuntimeConfig(event).public.rootDomain
  const now = Date.now()
  const domain = address.domain ? (({ token: _t, ...rest }) => rest)(address.domain) : null
  return { subdomain: tenant.subdomain, url: `https://${tenant.subdomain}.${root}`, previous: address.previous.filter(item => Date.parse(item.until) > now), domain }
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

const domainSchema = z.object({
  domain: z
    .string()
    .trim()
    .toLowerCase()
    .transform(value => value.replace(/^https?:\/\//, '').replace(/\/.*$/, '').replace(/\.$/, '')),
})

export const addDomain = defineMockRoute(({ event, body }) => {
  const { tenant, user } = requireAdmin(event)
  requireFeature(tenant, 'custom_domain')
  const { domain } = parseBody(domainSchema, body)
  const root = useRuntimeConfig(event).public.rootDomain
  if (!DOMAIN.test(domain) || domain === root || domain.endsWith(`.${root}`) || domain.endsWith('.formalie.com')) throw new MockError('FRM-GEN-1002', [{ field: 'domain', message: 'domain' }])
  const token = `formalie-verify=${crypto.randomUUID().replace(/-/g, '').slice(0, 24)}`
  const entry: CustomDomain & { token: string } = {
    domain,
    status: 'pending',
    records: [
      { type: 'CNAME', name: domain, value: `custom.${root}`, found: false },
      { type: 'TXT', name: `_formalie.${domain}`, value: token, found: false },
    ],
    added_at: new Date().toISOString(),
    checked_at: null,
    problem: null,
    token,
  }
  setDomain(tenant, entry)
  audit(event, tenant, user, 'domain', null, domain)
  return ok(view(event, tenant))
})

/** A DNS lookup that gives up after a few seconds. */
const lookup = <T>(work: Promise<T>) => Promise.race([work, new Promise<never>((_, reject) => setTimeout(() => reject(new Error('timeout')), 4000))])

export const checkDomain = defineMockRoute(async ({ event }) => {
  const { tenant, user } = requireAdmin(event)
  const entry = addressOf(tenant).domain
  if (!entry) throw new MockError('FRM-GEN-1004')
  const [cname, txt] = entry.records
  let problem: CustomDomain['problem']
  try {
    const targets = await lookup(resolveCname(cname!.name)).catch(error => ((error as { code?: string }).code === 'ENODATA' || (error as { code?: string }).code === 'ENOTFOUND' ? [] : Promise.reject(error)))
    cname!.found = targets.some(target => target.replace(/\.$/, '') === cname!.value)
    const texts = await lookup(resolveTxt(txt!.name)).catch(error => ((error as { code?: string }).code === 'ENODATA' || (error as { code?: string }).code === 'ENOTFOUND' ? [] : Promise.reject(error)))
    txt!.found = texts.some(parts => parts.join('') === entry.token)
    problem = cname!.found && txt!.found ? null : targets.length && !cname!.found ? 'wrong_target' : 'not_found'
  } catch {
    problem = 'dns_error'
  }
  const before = entry.status
  entry.status = problem ? (problem === 'wrong_target' ? 'failed' : 'pending') : 'verified'
  entry.problem = problem
  entry.checked_at = new Date().toISOString()
  setDomain(tenant, entry)
  if (before !== entry.status) audit(event, tenant, user, 'domain_status', before, entry.status)
  return ok(view(event, tenant))
})

export const removeDomain = defineMockRoute(({ event }) => {
  const { tenant, user } = requireAdmin(event)
  const entry = addressOf(tenant).domain
  if (entry) {
    setDomain(tenant, null)
    audit(event, tenant, user, 'domain', entry.domain, null)
  }
  return ok(view(event, tenant))
})

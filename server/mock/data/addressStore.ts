/**
 * Workspace address and own domain in the mock (F14 M7), kept in `.data/mock/addresses.json`: the
 * subdomain (changed in Settings; the old one keeps working for 90 days so links don't break) and an
 * own domain with the DNS records to add and its verification. Applied to the workspaces at start.
 */
import type { CustomDomain } from '#shared/types/address'
import { loadPersisted, savePersisted } from '../core/persist'
import { MOCK_TENANTS, type MockTenant } from './tenants'

export const REDIRECT_DAYS = 90

interface TenantAddress {
  subdomain: string
  previous: { subdomain: string; until: string }[]
  domain: (CustomDomain & { token: string }) | null
}

const stores = new Map<string, TenantAddress>(Object.entries(loadPersisted<Record<string, TenantAddress>>('addresses', {})))
const save = () => savePersisted('addresses', () => Object.fromEntries(stores))

// A changed subdomain survives restarts (sample workspaces too)
for (const tenant of MOCK_TENANTS) {
  const stored = stores.get(tenant.id)
  if (stored && stored.subdomain !== tenant.subdomain) tenant.subdomain = stored.subdomain
}

export function addressOf(tenant: MockTenant): TenantAddress {
  let address = stores.get(tenant.id)
  if (!address) {
    address = { subdomain: tenant.subdomain, previous: [], domain: null }
    stores.set(tenant.id, address)
  }
  return address
}

/** The workspace an old subdomain still points to (within the redirect window). */
export function tenantByPreviousSubdomain(subdomain: string): MockTenant | null {
  const now = Date.now()
  for (const [id, address] of stores)
    if (address.previous.some(item => item.subdomain === subdomain && Date.parse(item.until) > now)) return MOCK_TENANTS.find(tenant => tenant.id === id) ?? null
  return null
}

/** The workspace whose verified own domain this host is. */
export function tenantByDomain(host: string): MockTenant | null {
  for (const [id, address] of stores) if (address.domain?.status === 'verified' && address.domain.domain === host) return MOCK_TENANTS.find(tenant => tenant.id === id) ?? null
  return null
}

/** Is this subdomain in use, now or as someone's old address? */
export const subdomainTaken = (subdomain: string) => MOCK_TENANTS.some(tenant => tenant.subdomain === subdomain) || !!tenantByPreviousSubdomain(subdomain)

export function changeSubdomain(tenant: MockTenant, subdomain: string) {
  const address = addressOf(tenant)
  const until = new Date(Date.now() + REDIRECT_DAYS * 86_400_000).toISOString()
  address.previous = [{ subdomain: tenant.subdomain, until }, ...address.previous.filter(item => item.subdomain !== subdomain && Date.parse(item.until) > Date.now())].slice(0, 5)
  address.subdomain = subdomain
  tenant.subdomain = subdomain
  save()
}

export function setDomain(tenant: MockTenant, domain: (CustomDomain & { token: string }) | null) {
  addressOf(tenant).domain = domain
  save()
}

export const saveAddresses = save

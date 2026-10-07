/**
 * Workspace address in the mock (F14 M7), kept in `.data/mock/addresses.json`: the subdomain (changed
 * in Settings; the old one keeps working for 90 days so links don't break). Applied at start.
 */
import { loadPersisted, savePersisted } from '../core/persist'
import { MOCK_TENANTS, type MockTenant } from './tenants'

export const REDIRECT_DAYS = 90

interface TenantAddress {
  subdomain: string
  previous: { subdomain: string; until: string }[]
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
    address = { subdomain: tenant.subdomain, previous: [] }
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

export const saveAddresses = save

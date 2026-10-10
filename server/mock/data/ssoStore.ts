/**
 * Single sign-on connections in the mock (Settings → Sign-in, owner 2026-10-10), kept in `.data/mock/sso.json`:
 * one per workspace. The client secret stays here only (the backend keeps it encrypted).
 */
import { hasFeature } from '../core/plan'
import type { SsoConnection, SsoPublic } from '#shared/types/sso'
import { loadPersisted, savePersisted } from '../core/persist'
import type { MockTenant } from './tenants'

export type StoredSso = SsoConnection & { client_secret: string | null }

const stores = new Map<string, StoredSso>(Object.entries(loadPersisted<Record<string, StoredSso>>('sso', {})))
const save = () => savePersisted('sso', () => Object.fromEntries(stores))

export const ssoOf = (tenant: MockTenant): StoredSso | null => stores.get(tenant.id) ?? null

export function setSso(tenant: MockTenant, connection: StoredSso | null) {
  if (connection) stores.set(tenant.id, connection)
  else stores.delete(tenant.id)
  save()
}

/** For the sign-in page, only when it is switched on. */
export function ssoPublic(tenant: MockTenant): SsoPublic | null {
  const sso = ssoOf(tenant)
  return sso?.status === 'active' ? { provider: sso.provider, label: sso.label, domains: sso.domains, enforce: sso.enforce } : null
}

const domainOf = (email: string) => email.trim().toLowerCase().split('@').pop() ?? ''
/** Does this address belong to the single sign-on domains (a subdomain counts too)? */
export function ssoDomainMatch(tenant: MockTenant, email: string) {
  const sso = ssoPublic(tenant)
  const domain = domainOf(email)
  return !!sso && sso.domains.some(item => domain === item || domain.endsWith(`.${item}`))
}

/** People of these domains may only sign in through the provider. */
export const ssoRequired = (tenant: MockTenant, email: string) => hasFeature(tenant, 'sso') && !!ssoPublic(tenant)?.enforce && ssoDomainMatch(tenant, email)

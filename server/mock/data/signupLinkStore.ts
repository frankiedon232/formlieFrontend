/**
 * The workspace's shared sign-up link (F16 R3, `.data/mock/signup-links.json`): one link the organisation
 * can share (copy, QR code) so people ask to join; off until an admin turns it on; optional email domains
 * it accepts; a new link stops the old one. Everyone who signs up with it waits for approval.
 */
import { randomBytes } from 'node:crypto'
import { loadPersisted, savePersisted } from '../core/persist'
import type { MockTenant } from './tenants'

export interface SignupLink {
  enabled: boolean
  token: string
  /** Email domains it accepts (example.org); empty = any. */
  domains: string[]
  updated_at: string
}

const stores = new Map<string, SignupLink>(Object.entries(loadPersisted<Record<string, SignupLink>>('signup-links', {})))
export const saveSignupLinks = () => savePersisted('signup-links', () => Object.fromEntries(stores))
export const newSignupToken = () => `w${randomBytes(18).toString('base64url')}`

export function signupLinkOf(tenant: MockTenant): SignupLink {
  let link = stores.get(tenant.id)
  if (!link) {
    link = { enabled: false, token: newSignupToken(), domains: [], updated_at: new Date().toISOString() }
    stores.set(tenant.id, link)
    saveSignupLinks()
  }
  return link
}

/** The workspace whose shared link this is (only while it is on). */
export function tenantBySignupToken(tenants: MockTenant[], token: string): MockTenant | null {
  for (const tenant of tenants) {
    const link = stores.get(tenant.id)
    if (link?.enabled && link.token === token) return tenant
  }
  return null
}

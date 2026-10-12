import { z } from 'zod'
import type { H3Event } from 'h3'
import { hasFeature } from '../core/plan'
import type { SubdomainAvailability, TenantPublicProfile, WorkspaceLink } from '#shared/types/auth'
import { isValidSubdomain, RESERVED_SUBDOMAINS } from '#shared/utils/tenant/host'
import {
  createChallenge,
  describeChallenge,
  devMeta,
  tenantOf,
  verifyChallenge,
  consumeChallenge,
} from '../core/auth'
import { MockError, ok } from '../core/respond'
import { defineMockRoute } from '../core/route'
import { parseBody } from '../core/validate'
import { MOCK_TENANTS, MOCK_USERS } from '../data/tenants'
import { SIGNIN_PROVIDERS } from '#shared/utils/settings/schemas'
import { websiteOf } from './onboarding'
import { settingsOf } from '../data/settingsStore'
import { subdomainTaken } from '../data/addressStore'
import { ssoPublic } from '../data/ssoStore'

/** GET /tenants/public, branding + enabled sign-in methods for this host. */
export const publicProfile = defineMockRoute(({ event }) => {
  const { context, tenant } = tenantOf(event)
  if (context.kind === 'manage') {
    return ok<TenantPublicProfile>({
      mode: 'manage',
      name: 'Formalie',
      subdomain: 'manage',
      logo_url: null,
      colors: { primary: null },
      // Sign-up: email and password, Google, Facebook (owner, 2026-10-12)
      auth_providers: [...SIGNIN_PROVIDERS],
      status: 'active',
    })
  }
  if (!tenant) throw new MockError('FRM-TEN-1001')
  // The workspace's own name and branding from Settings (F14)
  const { company, branding, security } = settingsOf(tenant)
  return ok<TenantPublicProfile>({
    mode: 'tenant',
    name: company.display_name || tenant.name,
    subdomain: tenant.subdomain,
    logo_url: branding.logo_url,
    logo_dark_url: branding.logo_dark_url,
    favicon_url: branding.favicon_url,
    signin_message: branding.signin_message,
    colors: { primary: branding.brand_color },
    website: websiteOf(tenant),
    // Subscription (F24): other sign-in methods and single sign-on only while the plan has them
    // Always all of them; single sign-on shows too once the admin turns it on (sso below)
    auth_providers: [...SIGNIN_PROVIDERS],
    sso: hasFeature(tenant, 'sso') ? ssoPublic(tenant) : null,
    password_policy: { min_length: security.password.min_length, lower: security.password.lower, upper: security.password.upper, number: security.password.number, symbol: security.password.symbol },
    status: tenant.status,
    // B16: the platform admin's reason for a suspension; the mock has no platform admin
    status_reason: null,
  })
})

/** GET /tenants/subdomain-availability?subdomain= */
export const subdomainAvailability = defineMockRoute(({ query }) => {
  const value = String(query.subdomain ?? '')
    .trim()
    .toLowerCase()
  let reason: SubdomainAvailability['reason'] = null
  if (RESERVED_SUBDOMAINS.includes(value)) reason = 'reserved'
  else if (!isValidSubdomain(value) || value.length < 3) reason = 'invalid'
  else if (subdomainTaken(value)) reason = 'taken'
  return ok<SubdomainAvailability>({ available: reason === null, reason })
})

const emailSchema = z.object({ email: z.email() })

/** POST /tenants/find-workspace, always "sent" (no account enumeration). */
export const findWorkspace = defineMockRoute(({ body }) => {
  const { email } = parseBody(emailSchema, body)
  const challenge = createChallenge({
    purpose: 'find',
    email,
    user: null,
    tenant: null,
    channel: 'email',
    channels: ['email'],
  })
  return ok(describeChallenge(challenge), devMeta(challenge))
})

const verifySchema = z.object({ challenge_id: z.string(), code: z.string().regex(/^\d{6}$/) })

/** POST /tenants/find-workspace/verify → every workspace this email belongs to. */
/** The active workspaces this (already verified) email has an account in, with a sign-in link to each. */
export function workspacesOf(event: H3Event, email: string): WorkspaceLink[] {
  const { public: config } = useRuntimeConfig(event)
  const port = getRequestURL(event).port
  const address = email.toLowerCase()
  return MOCK_TENANTS.filter(
    tenant => tenant.status === 'active' && MOCK_USERS.some(u => u.tenant_id === tenant.id && u.email.toLowerCase() === address),
  ).map(tenant => ({
    name: tenant.name,
    subdomain: tenant.subdomain,
    url: `https://${tenant.subdomain}.${config.rootDomain}${port ? `:${port}` : ''}/auth/login?email=${encodeURIComponent(email)}`,
  }))
}

export const findWorkspaceVerify = defineMockRoute(({ event, body }) => {
  const { challenge_id, code } = parseBody(verifySchema, body)
  const challenge = verifyChallenge(challenge_id, code, 'find')
  consumeChallenge(challenge_id)
  return ok(workspacesOf(event, challenge.email))
})

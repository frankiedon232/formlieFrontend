import { z } from 'zod'
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
import { websiteOf } from './onboarding'

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
      // manage.* offers every provider for the first signup.
      auth_providers: ['password', 'google', 'microsoft', 'apple', 'facebook'],
      status: 'active',
    })
  }
  if (!tenant) throw new MockError('FRM-TEN-1001')
  return ok<TenantPublicProfile>({
    mode: 'tenant',
    name: tenant.name,
    subdomain: tenant.subdomain,
    logo_url: tenant.logo_url ?? null,
    colors: { primary: tenant.brand_color ?? null },
    website: websiteOf(tenant),
    auth_providers: tenant.auth_providers,
    status: tenant.status,
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
  else if (MOCK_TENANTS.some(t => t.subdomain === value)) reason = 'taken'
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
export const findWorkspaceVerify = defineMockRoute(({ event, body }) => {
  const { challenge_id, code } = parseBody(verifySchema, body)
  const challenge = verifyChallenge(challenge_id, code, 'find')
  consumeChallenge(challenge_id)
  const { public: config } = useRuntimeConfig(event)
  const port = getRequestURL(event).port
  const workspaces: WorkspaceLink[] = MOCK_TENANTS.filter(
    tenant =>
      tenant.status === 'active' &&
      MOCK_USERS.some(
        u => u.tenant_id === tenant.id && u.email.toLowerCase() === challenge.email.toLowerCase(),
      ),
  ).map(tenant => ({
    name: tenant.name,
    subdomain: tenant.subdomain,
    url: `https://${tenant.subdomain}.${config.rootDomain}${port ? `:${port}` : ''}/auth/login?email=${encodeURIComponent(challenge.email)}`,
  }))
  return ok(workspaces)
})

/**
 * Single sign-on (Settings → Sign-in, owner 2026-10-10; docs/API-CONTRACT.md → Settings). Admins only.
 *
 *   GET    /settings/sso            the connection (secret never returned) and what the identity provider needs
 *   PUT    /settings/sso            SsoSaveRequest (a changed set-up must be tested again)
 *   POST   /settings/sso/test       SAML: reads the metadata address (really) or checks the values given;
 *                                    OIDC: reads {issuer}/.well-known/openid-configuration (really)
 *   POST   /settings/sso/status     { active } (on only after a passing test, else FRM-AUTH-1020)
 *   DELETE /settings/sso
 *   GET    /auth/sso/start?email=   (plain redirect) the mock has no identity provider to send people to
 *
 * Everything is in the audit trail.
 */
import type { H3Event } from 'h3'
import { z } from 'zod'
import { SSO_PROTOCOL, SSO_PROVIDERS, type SsoProblem, type SsoServiceProvider, type SsoSettings } from '#shared/types/sso'
import { isEmailDomain } from '#shared/utils/settings/schemas'
import { actorOf, recordAudit } from '../core/audit'
import { requireAdmin } from '../core/auth'
import { MockError, ok } from '../core/respond'
import { defineMockRoute } from '../core/route'
import { parseBody } from '../core/validate'
import { workspaceUrl } from '../data/notificationStore'
import { rolesOf } from '../data/rolesStore'
import { setSso, ssoOf, type StoredSso } from '../data/ssoStore'
import type { MockTenant, MockUser } from '../data/tenants'

function serviceProvider(event: H3Event, tenant: MockTenant): SsoServiceProvider {
  const url = (path: string) => workspaceUrl(event, tenant, `/api/v1/auth/sso/${path}`)
  return { entity_id: url('saml/metadata'), acs_url: url('saml/acs'), metadata_url: url('saml/metadata'), redirect_uri: url('oidc/callback'), signout_url: url('signout') }
}
function view(event: H3Event, tenant: MockTenant): SsoSettings {
  const stored = ssoOf(tenant)
  const connection = stored ? (({ client_secret: _s, ...rest }) => rest)(stored) : null
  return { connection, service_provider: serviceProvider(event, tenant) }
}
const audit = (event: H3Event, tenant: MockTenant, user: MockUser, field: string, before: string | null, after: string | null) =>
  recordAudit(event, tenant, { action: 'settings.updated', actor: actorOf(user), resource: { type: 'setting', id: null, name: 'Single sign-on' }, changes: [{ field, before, after }] })

export const getSso = defineMockRoute(({ event }) => ok(view(event, requireAdmin(event).tenant)))

const url = z
  .string()
  .trim()
  .max(500)
  .nullable()
  .transform(value => value || null)
  .refine(value => !value || /^https:\/\/[^\s]+$/i.test(value), 'https')
const text = (max: number) =>
  z
    .string()
    .trim()
    .max(max)
    .nullable()
    .transform(value => value || null)
const saveSchema = z.object({
  provider: z.enum(SSO_PROVIDERS),
  label: z.string().trim().min(1).max(40),
  saml: z.object({ metadata_url: url, entity_id: text(500), sso_url: url, certificate: text(10_000) }).partial().optional(),
  oidc: z.object({ issuer: url, client_id: text(300), client_secret: z.string().max(1000).nullable().optional() }).optional(),
  domains: z.array(z.string().trim().toLowerCase().transform(value => value.replace(/^@/, '')).refine(isEmailDomain, 'domain')).max(20),
  enforce: z.boolean(),
  auto_create: z.boolean(),
  default_role: z.string().min(1).max(100),
})

export const saveSso = defineMockRoute(({ event, body }) => {
  const { tenant, user } = requireAdmin(event)
  const input = parseBody(saveSchema, body)
  if (input.default_role === 'owner' || !rolesOf(tenant).some(role => role.id === input.default_role)) throw new MockError('FRM-GEN-1002', [{ field: 'default_role', message: 'role' }])
  if (input.enforce && !input.domains.length) throw new MockError('FRM-GEN-1002', [{ field: 'domains', message: 'required' }])
  const current = ssoOf(tenant)
  const protocol = SSO_PROTOCOL[input.provider]
  const saml = { metadata_url: input.saml?.metadata_url ?? null, entity_id: input.saml?.entity_id ?? null, sso_url: input.saml?.sso_url ?? null, certificate: input.saml?.certificate ?? null }
  const secret = input.oidc?.client_secret === undefined ? (current?.client_secret ?? null) : input.oidc.client_secret || null
  const oidc = { issuer: input.oidc?.issuer ?? null, client_id: input.oidc?.client_id ?? null, has_secret: !!secret }
  // A different provider set-up must pass a new test before people use it
  const setupChanged =
    !current || current.provider !== input.provider || JSON.stringify(current.saml) !== JSON.stringify(saml) || current.oidc.issuer !== oidc.issuer || current.oidc.client_id !== oidc.client_id || input.oidc?.client_secret !== undefined
  const next: StoredSso = {
    provider: input.provider,
    protocol,
    label: input.label,
    saml,
    oidc,
    client_secret: secret,
    domains: [...new Set(input.domains)],
    enforce: input.enforce,
    auto_create: input.auto_create,
    default_role: input.default_role,
    status: setupChanged ? 'draft' : current!.status,
    tested_at: setupChanged ? null : current!.tested_at,
    problem: setupChanged ? null : current!.problem,
    updated_at: new Date().toISOString(),
  }
  setSso(tenant, next)
  audit(event, tenant, user, 'sso', current ? `${current.provider} (${current.status})` : null, `${next.provider} (${next.status})`)
  return ok(view(event, tenant))
})

/** Fetches a page from the provider, giving up after a few seconds. */
async function read(address: string): Promise<string | null> {
  try {
    const response = await fetch(address, { signal: AbortSignal.timeout(6000), headers: { accept: 'application/json, application/xml, text/xml' } })
    return response.ok ? await response.text() : null
  } catch {
    return null
  }
}
const trimSlash = (value: string) => value.replace(/\/+$/, '')

async function problemOf(sso: StoredSso): Promise<SsoProblem | null> {
  if (sso.protocol === 'oidc') {
    if (!sso.oidc.issuer || !sso.oidc.client_id || !sso.client_secret) return 'incomplete'
    const body = await read(`${trimSlash(sso.oidc.issuer)}/.well-known/openid-configuration`)
    if (body === null) return 'unreachable'
    try {
      const discovery = JSON.parse(body) as { issuer?: string; authorization_endpoint?: string }
      if (!discovery.authorization_endpoint) return 'not_discovery'
      return trimSlash(discovery.issuer ?? '') === trimSlash(sso.oidc.issuer) ? null : 'issuer_mismatch'
    } catch {
      return 'not_discovery'
    }
  }
  if (sso.saml.metadata_url) {
    const body = await read(sso.saml.metadata_url)
    if (body === null) return 'unreachable'
    return /EntityDescriptor/.test(body) && /SingleSignOnService/.test(body) ? null : 'not_metadata'
  }
  const certificate = sso.saml.certificate?.replace(/-----(BEGIN|END) CERTIFICATE-----|\s/g, '') ?? ''
  return sso.saml.entity_id && sso.saml.sso_url && /^[A-Za-z0-9+/=]{200,}$/.test(certificate) ? null : 'incomplete'
}

export const testSso = defineMockRoute(async ({ event }) => {
  const { tenant, user } = requireAdmin(event)
  const sso = ssoOf(tenant)
  if (!sso) throw new MockError('FRM-GEN-1004')
  const problem = await problemOf(sso)
  const before = sso.status
  // A passing test keeps an active connection active; a failing one turns it off so nobody gets stuck
  sso.status = problem ? 'draft' : sso.status === 'active' ? 'active' : 'tested'
  sso.problem = problem
  sso.tested_at = problem ? null : new Date().toISOString()
  setSso(tenant, sso)
  audit(event, tenant, user, 'sso_test', before, problem ?? 'passed')
  return ok(view(event, tenant))
})

const statusSchema = z.object({ active: z.boolean() })

export const setSsoStatus = defineMockRoute(({ event, body }) => {
  const { tenant, user } = requireAdmin(event)
  const { active } = parseBody(statusSchema, body)
  const sso = ssoOf(tenant)
  if (!sso) throw new MockError('FRM-GEN-1004')
  if (active && sso.status === 'draft') throw new MockError('FRM-AUTH-1020')
  const before = sso.status
  sso.status = active ? 'active' : 'tested'
  setSso(tenant, sso)
  if (before !== sso.status) audit(event, tenant, user, 'sso_status', before, sso.status)
  return ok(view(event, tenant))
})

export const removeSso = defineMockRoute(({ event }) => {
  const { tenant, user } = requireAdmin(event)
  const sso = ssoOf(tenant)
  if (sso) {
    setSso(tenant, null)
    audit(event, tenant, user, 'sso', sso.provider, null)
  }
  return ok(view(event, tenant))
})

/** GET /auth/sso/start, the mock can't reach the identity provider; the backend sends people there (SAML or OIDC). */
export const ssoStart = defineEventHandler(event => sendRedirect(event, '/auth/login?sso=unavailable', 302))

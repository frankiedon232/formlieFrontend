/**
 * Formalie support access, announcements and switches in the mock (B16, docs/API-CONTRACT.md → Formalie
 * support access, announcements and switches). Kept in `.data/mock/support.json`.
 *
 *   GET · POST · DELETE /settings/security/support-access          the consent (settings.view / settings.manage)
 *   POST /settings/security/support-access/requests/{id}/decline
 *   GET  /support-access/status                                     the live session banner, for everyone
 *   POST /auth/support/redeem { ticket }                            → AuthTokens + support (no refresh cookie)
 *   POST /auth/support/end                                          the support person leaves
 *   GET  /platform/announcements · /platform/feature-flags
 *
 * There is no platform admin in the mock: every workspace starts with one pending request from Formalie
 * (and its notice for the admins), and turning access on prints a one-time support link in the Nuxt
 * terminal, as the platform admin would hand it to a staff member. The audit trail names each step
 * (support.access_requested / _granted / _revoked, support.session_started / _ended); Formalie's own
 * steps show the staff member as a `system` actor with metadata.via = 'platform_admin', as the backend does.
 */
import type { H3Event } from 'h3'
import { z } from 'zod'
import type { FeatureFlags, PlatformAnnouncement, SupportAccessState, SupportBanner, SupportGrant, SupportMode, SupportRedeemResult, SupportRequest, SupportSessionRow } from '#shared/types/support'
import { SUPPORT_HOURS, SUPPORT_MODES } from '#shared/types/support'
import { actorOf, recordAudit } from '../core/audit'
import { bearerSessionId, requireAdmin, requireAuth, requireTenant, revokeSessions, startSupportSession, whenSupportRequest } from '../core/auth'
import { loadPersisted, savePersisted } from '../core/persist'
import { MockError, ok } from '../core/respond'
import { defineMockRoute } from '../core/route'
import { parseBody } from '../core/validate'
import { notificationsOf, workspaceUrl } from '../data/notificationStore'
import { can } from '../data/rolesStore'
import { MOCK_USERS, type MockTenant, type MockUser } from '../data/tenants'

const TICKET_MS = 2 * 60_000
const SESSION_MS = 60 * 60_000
const NEVER = /^\/(me\/|settings\/security\/support-access|privacy\/|settings\/sso)|\/(reveal|secret)(\/|$)/

interface StoredSession extends SupportSessionRow {
  grant_id: string
  ticket: string | null
  ticket_expires_at: number
  /** The mock auth session behind the support token, once redeemed. */
  auth_session: string | null
}
interface TenantSupport {
  grants: (SupportGrant & { revoked_at: string | null })[]
  requests: SupportRequest[]
  sessions: StoredSession[]
  seeded: boolean
}

const stores = new Map<string, TenantSupport>(Object.entries(loadPersisted<Record<string, TenantSupport>>('support', {})))
const save = () => savePersisted('support', () => Object.fromEntries(stores))
const iso = (ms: number) => new Date(ms).toISOString()

/** Formalie staff as the audit trail shows them: the backend sends platform support as `system` with the staff name. */
const staffActor = (name: string) => ({ type: 'system' as const, id: null, name, email: null })
const RESOURCE = { type: 'setting', id: null, name: 'Formalie support access' }

function adminsOf(tenant: MockTenant): MockUser[] {
  return MOCK_USERS.filter(user => user.tenant_id === tenant.id && !user.disabled && can(user, 'settings.manage'))
}

function storeOf(tenant: MockTenant, event?: H3Event): TenantSupport {
  let store = stores.get(tenant.id)
  if (!store) {
    store = { grants: [], requests: [], sessions: [], seeded: false }
    stores.set(tenant.id, store)
  }
  if (!store.seeded && event) {
    // One request from Formalie to try Approve / Decline with, and its notice for the admins
    store.seeded = true
    const request: SupportRequest = { id: crypto.randomUUID(), staff_name: 'Alex Morgan', reason: 'You asked why some responses are missing from the export. We would like to look at the form and its export settings.', mode: 'read', hours: 24, status: 'pending', created_at: iso(Date.now()), expires_at: iso(Date.now() + 7 * 86_400_000), decided_at: null, decided_by_name: null }
    store.requests.unshift(request)
    recordAudit(event, tenant, { action: 'support.access_requested', actor: staffActor(request.staff_name), resource: RESOURCE, metadata: { via: 'platform_admin', staff_reason: request.reason, mode: request.mode, hours: String(request.hours) } })
    const feed = notificationsOf(tenant)
    for (const admin of adminsOf(tenant)) feed.items.unshift({ id: crypto.randomUUID(), user_id: admin.id, event: 'support_request', params: { staff: request.staff_name, mode: request.mode, hours: request.hours, request_id: request.id }, link: '/settings/security', created_at: request.created_at, read_at: null })
    save()
  }
  return store
}

const activeGrant = (store: TenantSupport) => store.grants.find(grant => !grant.revoked_at && Date.parse(grant.expires_at) > Date.now()) ?? null
const isLive = (session: StoredSession) => !!session.started_at && !session.ended_at && Date.parse(session.ends_at) > Date.now()

function stateOf(tenant: MockTenant, event?: H3Event): SupportAccessState {
  const store = storeOf(tenant, event)
  const now = Date.now()
  for (const request of store.requests) if (request.status === 'pending' && Date.parse(request.expires_at) <= now) request.status = 'expired'
  const grant = activeGrant(store)
  return {
    grant: grant ? { id: grant.id, mode: grant.mode, hours: grant.hours, starts_at: grant.starts_at, expires_at: grant.expires_at, granted_by: grant.granted_by, request_id: grant.request_id } : null,
    requests: store.requests.filter(request => request.status === 'pending'),
    sessions: store.sessions
      .filter(session => session.started_at)
      .slice(0, 20)
      .map(({ id, staff_name, mode, started_at, ends_at, ended_at, ended_reason }) => ({ id, staff_name, mode, started_at, ends_at, ended_at, ended_reason, active: !!started_at && !ended_at && Date.parse(ends_at) > now })),
    hours: [...SUPPORT_HOURS],
    modes: [...SUPPORT_MODES],
  }
}

function endSessions(tenant: MockTenant, store: TenantSupport, reason: SupportSessionRow['ended_reason']) {
  const ended = store.sessions.filter(session => !session.ended_at)
  for (const session of ended) Object.assign(session, { ended_at: iso(Date.now()), ended_reason: session.started_at ? reason : 'not_used', ticket: null })
  const ids = ended.map(session => session.auth_session).filter((id): id is string => !!id)
  if (ids.length) revokeSessions(tenant, { ids })
  return ended.filter(session => session.started_at).length
}

/** The platform admin's part: a one-time ticket for a staff member, printed in the Nuxt terminal. */
function issueTicket(event: H3Event, tenant: MockTenant, store: TenantSupport, grant: SupportGrant, staff: string) {
  const ticket = crypto.randomUUID().replace(/-/g, '') + crypto.randomUUID().replace(/-/g, '').slice(0, 8)
  const ends = Math.min(Date.parse(grant.expires_at), Date.now() + SESSION_MS)
  store.sessions.unshift({ id: crypto.randomUUID(), staff_name: staff, mode: grant.mode, started_at: null, ends_at: iso(ends), ended_at: null, ended_reason: null, active: false, grant_id: grant.id, ticket, ticket_expires_at: Date.now() + TICKET_MS, auth_session: null })
  console.info(`[mock] Formalie support link for ${tenant.subdomain} (2 minutes, once): ${workspaceUrl(event, tenant, '/support')}#ticket=${ticket}`)
}

const allowSchema = z.object({ hours: z.union([z.literal(1), z.literal(24), z.literal(168)]), mode: z.enum(SUPPORT_MODES).default('read'), request_id: z.string().max(64).optional() })

export const getSupportAccess = defineMockRoute(({ event }) => ok(stateOf(requireAdmin(event).tenant, event)))

export const allowSupportAccess = defineMockRoute(({ event, body }) => {
  const { tenant, user } = requireAdmin(event)
  const input = parseBody(allowSchema, body)
  const store = storeOf(tenant, event)
  const asked = input.request_id ? store.requests.find(request => request.id === input.request_id) : null
  if (input.request_id && !asked) throw new MockError('FRM-GEN-1004')
  if (asked && (asked.status !== 'pending' || Date.parse(asked.expires_at) <= Date.now())) throw new MockError('FRM-GEN-1009', [{ field: 'request_id', message: asked.status }])
  const name = `${user.first_name} ${user.last_name}`.trim()
  let grant = activeGrant(store)
  const before = grant ? `${grant.mode} until ${grant.expires_at}` : null
  const expires = iso(Date.now() + input.hours * 3_600_000)
  if (grant) Object.assign(grant, { mode: input.mode, hours: input.hours, expires_at: expires, granted_by: { id: user.id, name }, request_id: input.request_id ?? grant.request_id })
  else {
    grant = { id: crypto.randomUUID(), mode: input.mode, hours: input.hours, starts_at: iso(Date.now()), expires_at: expires, granted_by: { id: user.id, name }, request_id: input.request_id ?? null, revoked_at: null }
    store.grants.unshift(grant)
  }
  if (asked) Object.assign(asked, { status: 'approved', decided_at: iso(Date.now()), decided_by_name: name })
  recordAudit(event, tenant, { action: 'support.access_granted', actor: actorOf(user), resource: RESOURCE, changes: [{ field: 'support_access', before, after: `${grant.mode} until ${grant.expires_at}` }], metadata: { mode: input.mode, hours: String(input.hours), ...(asked ? { request_id: asked.id } : {}) } })
  issueTicket(event, tenant, store, grant, asked?.staff_name ?? 'Alex Morgan')
  save()
  return ok(stateOf(tenant))
})

export const revokeSupportAccess = defineMockRoute(({ event }) => {
  const { tenant, user } = requireAdmin(event)
  const store = storeOf(tenant, event)
  const grant = activeGrant(store)
  const ended = endSessions(tenant, store, 'access_ended')
  if (grant) {
    grant.revoked_at = iso(Date.now())
    recordAudit(event, tenant, { action: 'support.access_revoked', actor: actorOf(user), resource: RESOURCE, changes: [{ field: 'support_access', before: `${grant.mode} until ${grant.expires_at}`, after: null }], metadata: { sessions_ended: String(ended) } })
  }
  save()
  return ok(stateOf(tenant))
})

export const declineSupportRequest = defineMockRoute(({ event }) => {
  const { tenant, user } = requireAdmin(event)
  const store = storeOf(tenant, event)
  const asked = store.requests.find(request => request.id === getRouterParam(event, 'id'))
  if (!asked) throw new MockError('FRM-GEN-1004')
  if (asked.status !== 'pending') throw new MockError('FRM-GEN-1009', [{ field: 'request_id', message: asked.status }])
  Object.assign(asked, { status: 'declined', decided_at: iso(Date.now()), decided_by_name: `${user.first_name} ${user.last_name}`.trim() })
  recordAudit(event, tenant, { action: 'settings.updated', actor: actorOf(user), resource: RESOURCE, changes: [{ field: 'support_access_request', before: 'pending', after: 'declined' }] })
  save()
  return ok(stateOf(tenant))
})

/** The live support session everyone sees a banner for (also `support_session` in GET /me). */
export function supportBannerOf(tenant: MockTenant): SupportBanner | null {
  const live = storeOf(tenant).sessions.filter(isLive).sort((a, b) => Date.parse(b.ends_at) - Date.parse(a.ends_at))[0]
  return live ? { active: true, staff_name: live.staff_name, mode: live.mode, started_at: live.started_at!, ends_at: live.ends_at } : null
}

/** True when this request comes from a support session (GET /me `is_support`). */
export const isSupportRequest = (event: H3Event) => {
  const sid = bearerSessionId(event)
  return !!sid && [...stores.values()].some(store => store.sessions.some(item => item.auth_session === sid))
}

export const supportStatus = defineMockRoute(({ event }) => {
  const { tenant } = requireAuth(event)
  return ok(supportBannerOf(tenant))
})

const ticketSchema = z.object({ ticket: z.string().min(20).max(100) })

export const redeemSupportTicket = defineMockRoute(({ event, body }) => {
  const tenant = requireTenant(event)
  const { ticket } = parseBody(ticketSchema, body)
  const store = storeOf(tenant, event)
  const session = store.sessions.find(item => item.ticket === ticket)
  const grant = session ? store.grants.find(item => item.id === session.grant_id) : undefined
  if (!session || session.started_at || session.ended_at || session.ticket_expires_at <= Date.now() || !grant || grant.revoked_at || Date.parse(grant.expires_at) <= Date.now()) throw new MockError('FRM-AUTH-1010')
  const owner = MOCK_USERS.find(user => user.tenant_id === tenant.id && user.role === 'owner' && !user.disabled)
  if (!owner) throw new MockError('FRM-AUTH-1010')
  const mode: SupportMode = session.mode === 'write' && grant.mode === 'write' ? 'write' : 'read'
  const acting: MockUser = { ...owner, first_name: 'Formalie support', last_name: session.staff_name, email: 'support@formalie.com', photo: null }
  const { sessionId, tokens } = startSupportSession(event, acting, tenant, Date.parse(session.ends_at))
  Object.assign(session, { started_at: iso(Date.now()), ticket: null, auth_session: sessionId, mode })
  recordAudit(event, tenant, { action: 'auth.login.succeeded', actor: actorOf(acting), metadata: { method: 'support', mode } })
  const reason = store.requests.find(item => item.id === grant.request_id)?.reason
  recordAudit(event, tenant, { action: 'support.session_started', actor: staffActor(session.staff_name), resource: RESOURCE, metadata: { via: 'platform_admin', mode, ends_at: session.ends_at, ...(reason ? { staff_reason: reason } : {}) } })
  save()
  return ok<SupportRedeemResult>({ ...tokens, user: { ...tokens.user, support: true }, support: { session_id: session.id, mode, staff_name: session.staff_name, ends_at: session.ends_at } })
})

export const endSupportSession = defineMockRoute(({ event }) => {
  const tenant = requireTenant(event)
  const sid = bearerSessionId(event)
  const store = storeOf(tenant, event)
  const session = sid ? store.sessions.find(item => item.auth_session === sid && !item.ended_at) : undefined
  if (!session) return ok({ signed_out: false })
  Object.assign(session, { ended_at: iso(Date.now()), ended_reason: 'signed_out' })
  recordAudit(event, tenant, { action: 'support.session_ended', actor: staffActor(session.staff_name), resource: RESOURCE, metadata: { via: 'platform_admin', ended_reason: 'signed_out' } })
  revokeSessions(tenant, { ids: [sid!] })
  save()
  return ok({ signed_out: true })
})

// Every call of a support session: read only unless both allow changes; some areas never
whenSupportRequest((sessionId, method, path) => {
  for (const store of stores.values()) {
    const session = store.sessions.find(item => item.auth_session === sessionId)
    if (!session) continue
    const clean = path.split('?')[0] ?? ''
    if (NEVER.test(clean)) throw new MockError('FRM-PERM-1001', [{ field: 'support', message: 'not_in_support_sessions' }])
    const grant = store.grants.find(item => item.id === session.grant_id)
    const write = session.mode === 'write' && grant?.mode === 'write'
    if (!write && !['GET', 'HEAD', 'OPTIONS'].includes(method.toUpperCase())) throw new MockError('FRM-PERM-1001', [{ field: 'support', message: 'read_only' }])
    return
  }
})

const ANNOUNCEMENTS: PlatformAnnouncement[] = [
  { id: 'ann-languages', kind: 'news', tone: 'info', title: 'Formalie now speaks 20 languages', body: 'Forms, emails and the whole portal follow each person’s language.', link_url: null, dismissible: true, starts_at: '2026-10-01T00:00:00.000Z', ends_at: null },
]

export const platformAnnouncements = defineMockRoute(({ event }) => {
  requireAuth(event)
  return ok(ANNOUNCEMENTS)
})

export const platformFeatureFlags = defineMockRoute(({ event }) => {
  requireAuth(event)
  return ok<FeatureFlags>({})
})

/**
 * Mock auth core (docs/SECURITY-PROTOCOL.md §5, §7): host → tenant, OTP challenges,
 * 15-min access tokens, single-use rotating refresh tokens in an HttpOnly cookie with
 * family revocation on reuse, one-time login tickets for cross-subdomain hand-off.
 */
import type { H3Event } from 'h3'
import type { AuthTokens, LoginChallenge, OtpChannel } from '#shared/types/auth'
import type { ActiveSession } from '#shared/types/settings'
import type { AuditDevice } from '#shared/types/audit'
import { ipInCidr } from '#shared/utils/apiService/access'
import { resolveHostContext, type HostContext } from '#shared/utils/tenant/host'
import { actorOf, deviceFrom, recordAudit } from './audit'
import { loadPersisted, savePersisted } from './persist'
import { MockError } from './respond'
import { tenantByDomain, tenantByPreviousSubdomain } from '../data/addressStore'
import { settingsOf } from '../data/settingsStore'
import { MOCK_TENANTS, MOCK_USERS, type MockTenant, type MockUser } from '../data/tenants'

const ACCESS_TTL_S = 15 * 60
const REFRESH_TTL_S = 7 * 24 * 60 * 60
/** Signed out after this long without any activity (owner, 2026-10-02: at least 1 hour); each workspace sets its own in Settings → Security (F14 M3). */
export const IDLE_TIMEOUT_MS = 60 * 60 * 1000
const OTP_TTL_MS = 5 * 60 * 1000
const OTP_MAX_ATTEMPTS = 5

/** The workspace's session limits in milliseconds (Settings → Security). */
function sessionLimits(tenant: MockTenant) {
  const { sessions } = settingsOf(tenant).security
  return { idle: sessions.idle_minutes * 60_000, max: sessions.max_hours * 3_600_000 }
}

/** The caller's address (behind the dev proxy too), without the IPv4-in-IPv6 prefix. */
export const callerIp = (event: H3Event) => (getRequestIP(event, { xForwardedFor: true }) ?? 'unknown').replace(/^::ffff:/i, '')

/** True when the workspace has no allowlist, or the address is on it (Settings → Security). */
export function ipAllowed(tenant: MockTenant, ip: string): boolean {
  const list = settingsOf(tenant).security.ip_allowlist
  return !list.enabled || list.entries.some(entry => ipInCidr(ip, entry.value))
}
const OTP_RESEND_AFTER_S = 60
const OTP_MAX_RESENDS = 3
export const REFRESH_COOKIE = 'formalie_rt'
const REFRESH_COOKIE_PATH = '/api/v1/auth'
/** Dev-only header so localhost / LAN-IP sessions can target a tenant (decision 19). */
export const DEV_TENANT_HEADER = 'x-formalie-dev-tenant'

const randomToken = (bytes = 32) =>
  Array.from(crypto.getRandomValues(new Uint8Array(bytes)), b => b.toString(16).padStart(2, '0')).join('')

// ── Tenant from host ────────────────────────────────────────────────────────────────

export interface RequestTenant {
  context: HostContext
  tenant: MockTenant | null
}

export function tenantOf(event: H3Event): RequestTenant {
  const { public: config } = useRuntimeConfig(event)
  const context = resolveHostContext(getRequestHost(event, { xForwardedHost: true }), {
    rootDomain: config.rootDomain,
    manageSubdomain: config.manageSubdomain,
    tenantOverride: getHeader(event, DEV_TENANT_HEADER) ?? null,
  })
  // A subdomain that changed keeps working for a while (Settings → Address and domain); an own domain once verified
  const tenant =
    context.kind === 'tenant'
      ? (MOCK_TENANTS.find(t => t.subdomain === context.subdomain) ?? tenantByPreviousSubdomain(context.subdomain))
      : context.kind === 'custom'
        ? tenantByDomain(context.host)
        : null
  if (context.kind === 'custom' && tenant) return { context: { kind: 'tenant', host: context.host, subdomain: tenant.subdomain } as HostContext, tenant }
  return { context, tenant }
}

/** The active workspace of this host, or the right FRM-TEN error. */
export function requireTenant(event: H3Event): MockTenant {
  const { context, tenant } = tenantOf(event)
  if (context.kind !== 'tenant' || !tenant) throw new MockError('FRM-TEN-1001')
  if (tenant.status === 'suspended') throw new MockError('FRM-TEN-1002')
  return tenant
}

// ── OTP challenges ──────────────────────────────────────────────────────────────────

export type ChallengePurpose = 'login' | 'signup' | 'find' | 'reset'

export interface Challenge {
  id: string
  purpose: ChallengePurpose
  email: string
  user: MockUser | null
  tenant: MockTenant | null
  channel: OtpChannel
  channels: OtpChannel[]
  code: string
  expiresAt: number
  attempts: number
  resends: number
  lastSentAt: number
  verified: boolean
  /** How long a code lasts and how many tries it allows (the workspace's code rules). */
  ttlMs: number
  maxAttempts: number
  /** Signup: the account details waiting for the workspace step. */
  signup?: { first_name: string; last_name: string; password: string }
}

const challenges = new Map<string, Challenge>()

function mask(email: string): string {
  const [name = '', domain = ''] = email.split('@')
  return `${name.slice(0, 1)}${'•'.repeat(Math.max(1, name.length - 2))}${name.slice(-1)}@${domain}`
}

function sendCode(challenge: Challenge) {
  challenge.code = String(Math.floor(100000 + Math.random() * 900000))
  challenge.expiresAt = Date.now() + challenge.ttlMs
  challenge.lastSentAt = Date.now()
  console.info(`[mock-otp] ${challenge.purpose} code for ${challenge.email}: ${challenge.code}`)
}

export function createChallenge(
  input: Omit<Challenge, 'id' | 'code' | 'expiresAt' | 'attempts' | 'resends' | 'lastSentAt' | 'verified' | 'ttlMs' | 'maxAttempts'>,
) {
  // A workspace's own code rules (Settings → Sign-in); the defaults elsewhere
  const rules = input.tenant ? settingsOf(input.tenant).signin.code : null
  const challenge: Challenge = {
    ...input,
    ttlMs: rules ? rules.expiry_minutes * 60_000 : OTP_TTL_MS,
    maxAttempts: rules?.max_attempts ?? OTP_MAX_ATTEMPTS,
    id: crypto.randomUUID(),
    code: '',
    expiresAt: 0,
    attempts: 0,
    resends: 0,
    lastSentAt: 0,
    verified: false,
  }
  sendCode(challenge)
  challenges.set(challenge.id, challenge)
  return challenge
}

export function describeChallenge(challenge: Challenge): LoginChallenge {
  return {
    challenge_id: challenge.id,
    channels: challenge.channels,
    channel: challenge.channel,
    masked_destination: mask(challenge.email),
    resend_after: OTP_RESEND_AFTER_S,
    expires_at: new Date(challenge.expiresAt).toISOString(),
  }
}

/** Mock only: lets the dev code screen show the code. A real backend never returns it. */
export const devMeta = (challenge: Challenge) => ({ dev_code: challenge.code })

export function verifyChallenge(id: string, code: string, purpose: ChallengePurpose): Challenge {
  const challenge = challenges.get(id)
  if (!challenge || challenge.purpose !== purpose || challenge.expiresAt < Date.now()) {
    throw new MockError('FRM-AUTH-1003')
  }
  if (challenge.attempts >= challenge.maxAttempts) throw new MockError('FRM-AUTH-1004')
  if (challenge.code !== code) {
    challenge.attempts++
    const left = challenge.maxAttempts - challenge.attempts
    if (left <= 0) throw new MockError('FRM-AUTH-1004')
    throw new MockError('FRM-AUTH-1003', [{ field: 'attempts_left', message: String(left) }])
  }
  challenge.verified = true
  return challenge
}

export function resendChallenge(id: string, channel: OtpChannel | undefined): Challenge {
  const challenge = challenges.get(id)
  if (!challenge || challenge.verified) throw new MockError('FRM-AUTH-1003')
  if (challenge.resends >= OTP_MAX_RESENDS) throw new MockError('FRM-AUTH-1004')
  if (Date.now() - challenge.lastSentAt < OTP_RESEND_AFTER_S * 1000) throw new MockError('FRM-GEN-1029')
  if (channel && challenge.channels.includes(channel)) challenge.channel = channel
  challenge.resends++
  challenge.attempts = 0
  sendCode(challenge)
  return challenge
}

export const getChallenge = (id: string) => challenges.get(id) ?? null
export const consumeChallenge = (id: string) => challenges.delete(id)

// ── Sessions and tokens ─────────────────────────────────────────────────────────────

export interface Session {
  id: string
  user: MockUser
  tenant: MockTenant
  revoked: boolean
  /** Last request or refresh; the idle timeout counts from here. */
  lastActiveAt: number
  /** Sign-in time; the maximum session length counts from here. */
  startedAt: number
  ip: string
  device: AuditDevice
}

interface StoredSessions {
  sessions: { id: string; userId: string; tenantId: string; revoked: boolean; lastActiveAt: number; startedAt?: number; ip?: string; device?: AuditDevice }[]
  access: [string, { sid: string; expiresAt: number }][]
  refresh: [string, { sid: string; used: boolean; expiresAt: number }][]
}

const sessions = new Map<string, Session>()
const accessTokens = new Map<string, { sid: string; expiresAt: number }>()
const refreshTokens = new Map<string, { sid: string; used: boolean; expiresAt: number }>()

// Restore sessions saved before the last dev reload (see ./persist.ts).
{
  const stored = loadPersisted<StoredSessions>('sessions', { sessions: [], access: [], refresh: [] })
  const now = Date.now()
  for (const item of stored.sessions) {
    const user = MOCK_USERS.find(u => u.id === item.userId)
    const tenant = MOCK_TENANTS.find(t => t.id === item.tenantId)
    // The workspace's own limits are checked on every request (idleExpired)
    if (user && tenant && !item.revoked && now - item.lastActiveAt < 12 * IDLE_TIMEOUT_MS)
      sessions.set(item.id, { id: item.id, user, tenant, revoked: false, lastActiveAt: item.lastActiveAt, startedAt: item.startedAt ?? item.lastActiveAt, ip: item.ip ?? 'unknown', device: item.device ?? { type: 'unknown', browser: null, os: null } })
  }
  for (const [token, entry] of stored.access)
    if (sessions.has(entry.sid) && entry.expiresAt > now) accessTokens.set(token, entry)
  for (const [token, entry] of stored.refresh)
    if (sessions.has(entry.sid) && entry.expiresAt > now) refreshTokens.set(token, entry)
}

function persistSessions() {
  savePersisted('sessions', (): StoredSessions => {
    const now = Date.now()
    return {
      sessions: [...sessions.values()]
        .filter(s => !s.revoked && now - s.lastActiveAt < sessionLimits(s.tenant).idle)
        .map(s => ({
          id: s.id,
          userId: s.user.id,
          tenantId: s.tenant.id,
          revoked: s.revoked,
          lastActiveAt: s.lastActiveAt,
          startedAt: s.startedAt,
          ip: s.ip,
          device: s.device,
        })),
      access: [...accessTokens].filter(([, e]) => e.expiresAt > now && sessions.has(e.sid)),
      // Used tokens are kept too, so reuse is still detected after a reload.
      refresh: [...refreshTokens].filter(([, e]) => e.expiresAt > now && sessions.has(e.sid)),
    }
  })
}

/** True (and the session ends) when nothing happened for longer than the idle timeout, or it reached its maximum length. */
function idleExpired(session: Session): boolean {
  const limits = sessionLimits(session.tenant)
  if (Date.now() - session.lastActiveAt <= limits.idle && Date.now() - session.startedAt <= limits.max) return false
  session.revoked = true
  persistSessions()
  return true
}

function touch(session: Session) {
  session.lastActiveAt = Date.now()
  persistSessions()
}
const tickets = new Map<string, { user: MockUser; tenant: MockTenant; expiresAt: number }>()

function setRefreshCookie(event: H3Event, token: string) {
  setCookie(event, REFRESH_COOKIE, token, {
    httpOnly: true,
    secure: true,
    sameSite: 'strict',
    path: REFRESH_COOKIE_PATH,
    maxAge: REFRESH_TTL_S,
  })
}

function tokensFor(event: H3Event, session: Session): AuthTokens {
  const access = randomToken()
  accessTokens.set(access, { sid: session.id, expiresAt: Date.now() + ACCESS_TTL_S * 1000 })
  const refresh = randomToken()
  refreshTokens.set(refresh, { sid: session.id, used: false, expiresAt: Date.now() + REFRESH_TTL_S * 1000 })
  setRefreshCookie(event, refresh)
  touch(session)
  const { user, tenant } = session
  return {
    access_token: access,
    expires_in: ACCESS_TTL_S,
    user: {
      id: user.id,
      first_name: user.first_name,
      last_name: user.last_name,
      email: user.email,
      avatar_url: null,
      role: user.role,
    },
    tenant: { id: tenant.id, name: tenant.name, subdomain: tenant.subdomain },
    organisation: tenant.organisation,
  }
}

export function startSession(event: H3Event, user: MockUser, tenant: MockTenant): AuthTokens {
  const now = Date.now()
  const session: Session = { id: crypto.randomUUID(), user, tenant, revoked: false, lastActiveAt: now, startedAt: now, ip: callerIp(event), device: deviceFrom(getHeader(event, 'user-agent') ?? '') }
  sessions.set(session.id, session)
  return tokensFor(event, session)
}

/** POST /auth/refresh: single use; reusing an old token revokes the whole session (FRM-AUTH-1012). */
export function rotateRefresh(event: H3Event): AuthTokens {
  const token = getCookie(event, REFRESH_COOKIE)
  const entry = token ? refreshTokens.get(token) : undefined
  if (!token || !entry || entry.expiresAt < Date.now()) throw new MockError('FRM-AUTH-1010')
  const session = sessions.get(entry.sid)
  if (!session || session.revoked) throw new MockError('FRM-AUTH-1011')
  // Idle too long → plain "session expired" (the client then shows the sign-in page with that notice).
  if (idleExpired(session)) throw new MockError('FRM-AUTH-1001')
  if (entry.used) {
    session.revoked = true
    deleteCookie(event, REFRESH_COOKIE, { path: REFRESH_COOKIE_PATH })
    recordAudit(event, session.tenant, {
      action: 'auth.session.revoked',
      actor: actorOf(session.user),
      outcome: 'blocked',
      reason: 'FRM-AUTH-1012',
      metadata: { cause: 'refresh_token_reuse' },
    })
    throw new MockError('FRM-AUTH-1012')
  }
  if (session.tenant.id !== requireTenant(event).id) throw new MockError('FRM-TEN-1003')
  entry.used = true
  return tokensFor(event, session)
}

/** Revokes the session behind the refresh cookie and / or bearer; returns it (for the audit trail). */
export function endSession(event: H3Event): Session | null {
  const token = getCookie(event, REFRESH_COOKIE)
  const refreshEntry = token ? refreshTokens.get(token) : undefined
  const bearer = getHeader(event, 'authorization')?.replace(/^Bearer /, '')
  const accessEntry = bearer ? accessTokens.get(bearer) : undefined
  let ended: Session | null = null
  for (const sid of [refreshEntry?.sid, accessEntry?.sid]) {
    const session = sid ? sessions.get(sid) : undefined
    if (session && !session.revoked) {
      session.revoked = true
      ended = session
    }
  }
  deleteCookie(event, REFRESH_COOKIE, { path: REFRESH_COOKIE_PATH })
  persistSessions()
  return ended
}

/** Protected routes: valid bearer for this host's tenant, else FRM-AUTH-1001 / 1010 / 1011 / TEN-1003. */
export function requireAuth(event: H3Event): { user: MockUser; tenant: MockTenant } {
  const bearer = getHeader(event, 'authorization')?.replace(/^Bearer /, '')
  if (!bearer) throw new MockError('FRM-AUTH-1001')
  const entry = accessTokens.get(bearer)
  // Unknown or expired access token → 1001, so the client tries the refresh cookie before signing out.
  if (!entry || entry.expiresAt < Date.now()) throw new MockError('FRM-AUTH-1001')
  const session = sessions.get(entry.sid)
  if (!session || session.revoked) throw new MockError('FRM-AUTH-1011')
  if (idleExpired(session)) throw new MockError('FRM-AUTH-1001')
  if (session.tenant.id !== requireTenant(event).id) throw new MockError('FRM-TEN-1003')
  // Settings → Security: only from the allowed networks
  if (!ipAllowed(session.tenant, callerIp(event))) throw new MockError('FRM-AUTH-1016')
  // Throttled: activity is recorded at most once a minute per session.
  if (Date.now() - session.lastActiveAt > 60_000) touch(session)
  return { user: session.user, tenant: session.tenant }
}

/** Workspace owner / admin only (until Roles & access, F22). */
export function requireAdmin(event: H3Event): { user: MockUser; tenant: MockTenant } {
  const auth = requireAuth(event)
  if (auth.user.role === 'member') throw new MockError('FRM-PERM-1001')
  return auth
}

export function issueTicket(user: MockUser, tenant: MockTenant): string {
  const ticket = randomToken(24)
  tickets.set(ticket, { user, tenant, expiresAt: Date.now() + 2 * 60 * 1000 })
  return ticket
}

export function redeemTicket(event: H3Event, ticket: string): AuthTokens {
  const entry = tickets.get(ticket)
  tickets.delete(ticket)
  if (!entry || entry.expiresAt < Date.now()) throw new MockError('FRM-AUTH-1010')
  if (entry.tenant.id !== requireTenant(event).id) throw new MockError('FRM-TEN-1003')
  return startSession(event, entry.user, entry.tenant)
}

export const findUser = (email: string, tenantId: string) =>
  MOCK_USERS.find(user => user.email.toLowerCase() === email.toLowerCase() && user.tenant_id === tenantId) ??
  null

// ── Active sessions (Settings → Security) ───────────────────────────────────────────

/** The session behind this request's bearer. */
export function currentSessionId(event: H3Event): string | null {
  const bearer = getHeader(event, 'authorization')?.replace(/^Bearer /, '')
  return (bearer && accessTokens.get(bearer)?.sid) || null
}

/** The workspace's signed-in sessions, most recently active first. */
export function activeSessions(event: H3Event, tenant: MockTenant): ActiveSession[] {
  const current = currentSessionId(event)
  const limits = sessionLimits(tenant)
  const now = Date.now()
  return [...sessions.values()]
    .filter(s => s.tenant.id === tenant.id && !s.revoked && now - s.lastActiveAt <= limits.idle && now - s.startedAt <= limits.max)
    .sort((a, b) => b.lastActiveAt - a.lastActiveAt)
    .map(s => ({
      id: s.id,
      user: { name: `${s.user.first_name} ${s.user.last_name}`.trim(), email: s.user.email },
      current: s.id === current,
      started_at: new Date(s.startedAt).toISOString(),
      last_active_at: new Date(s.lastActiveAt).toISOString(),
      ip: s.ip,
      device: s.device,
    }))
}

/** Ends sessions of the workspace (all but `keep`, or only `ids`); returns the ended ones. */
export function revokeSessions(tenant: MockTenant, options: { ids?: string[]; keep?: string | null }): Session[] {
  const ended = [...sessions.values()].filter(s => s.tenant.id === tenant.id && !s.revoked && s.id !== options.keep && (!options.ids || options.ids.includes(s.id)))
  for (const s of ended) s.revoked = true
  if (ended.length) persistSessions()
  return ended
}

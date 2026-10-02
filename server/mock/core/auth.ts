/**
 * Mock auth core (docs/SECURITY-PROTOCOL.md §5, §7): host → tenant, OTP challenges,
 * 15-min access tokens, single-use rotating refresh tokens in an HttpOnly cookie with
 * family revocation on reuse, one-time login tickets for cross-subdomain hand-off.
 */
import type { H3Event } from 'h3'
import type { AuthTokens, LoginChallenge, OtpChannel } from '#shared/types/auth'
import { resolveHostContext, type HostContext } from '#shared/utils/tenant/host'
import { MockError } from './respond'
import { MOCK_TENANTS, MOCK_USERS, type MockTenant, type MockUser } from '../data/tenants'

const ACCESS_TTL_S = 15 * 60
const REFRESH_TTL_S = 7 * 24 * 60 * 60
const OTP_TTL_MS = 5 * 60 * 1000
const OTP_MAX_ATTEMPTS = 5
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
  const tenant =
    context.kind === 'tenant' ? (MOCK_TENANTS.find(t => t.subdomain === context.subdomain) ?? null) : null
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
  challenge.expiresAt = Date.now() + OTP_TTL_MS
  challenge.lastSentAt = Date.now()
  console.info(`[mock-otp] ${challenge.purpose} code for ${challenge.email}: ${challenge.code}`)
}

export function createChallenge(
  input: Omit<Challenge, 'id' | 'code' | 'expiresAt' | 'attempts' | 'resends' | 'lastSentAt' | 'verified'>,
) {
  const challenge: Challenge = {
    ...input,
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
  if (challenge.attempts >= OTP_MAX_ATTEMPTS) throw new MockError('FRM-AUTH-1004')
  if (challenge.code !== code) {
    challenge.attempts++
    const left = OTP_MAX_ATTEMPTS - challenge.attempts
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

interface Session {
  id: string
  user: MockUser
  tenant: MockTenant
  revoked: boolean
}

const sessions = new Map<string, Session>()
const accessTokens = new Map<string, { sid: string; expiresAt: number }>()
const refreshTokens = new Map<string, { sid: string; used: boolean; expiresAt: number }>()
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
    },
    tenant: { id: tenant.id, name: tenant.name, subdomain: tenant.subdomain },
    organisation: tenant.organisation,
  }
}

export function startSession(event: H3Event, user: MockUser, tenant: MockTenant): AuthTokens {
  const session: Session = { id: crypto.randomUUID(), user, tenant, revoked: false }
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
  if (entry.used) {
    session.revoked = true
    deleteCookie(event, REFRESH_COOKIE, { path: REFRESH_COOKIE_PATH })
    throw new MockError('FRM-AUTH-1012')
  }
  if (session.tenant.id !== requireTenant(event).id) throw new MockError('FRM-TEN-1003')
  entry.used = true
  return tokensFor(event, session)
}

export function endSession(event: H3Event) {
  const token = getCookie(event, REFRESH_COOKIE)
  const entry = token ? refreshTokens.get(token) : undefined
  if (entry) {
    const session = sessions.get(entry.sid)
    if (session) session.revoked = true
  }
  const bearer = getHeader(event, 'authorization')?.replace(/^Bearer /, '')
  const access = bearer ? accessTokens.get(bearer) : undefined
  if (access) {
    const session = sessions.get(access.sid)
    if (session) session.revoked = true
  }
  deleteCookie(event, REFRESH_COOKIE, { path: REFRESH_COOKIE_PATH })
}

/** Protected routes: valid bearer for this host's tenant, else FRM-AUTH-1001 / 1010 / 1011 / TEN-1003. */
export function requireAuth(event: H3Event): { user: MockUser; tenant: MockTenant } {
  const bearer = getHeader(event, 'authorization')?.replace(/^Bearer /, '')
  if (!bearer) throw new MockError('FRM-AUTH-1001')
  const entry = accessTokens.get(bearer)
  if (!entry) throw new MockError('FRM-AUTH-1010')
  if (entry.expiresAt < Date.now()) throw new MockError('FRM-AUTH-1001')
  const session = sessions.get(entry.sid)
  if (!session || session.revoked) throw new MockError('FRM-AUTH-1011')
  if (session.tenant.id !== requireTenant(event).id) throw new MockError('FRM-TEN-1003')
  return { user: session.user, tenant: session.tenant }
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

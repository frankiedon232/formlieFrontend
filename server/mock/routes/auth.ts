import { z } from 'zod'
import type { SignupComplete } from '#shared/types/auth'
import {
  consumeChallenge,
  createChallenge,
  describeChallenge,
  devMeta,
  endSession,
  findUser,
  getChallenge,
  issueTicket,
  redeemTicket,
  requireAuth,
  requireTenant,
  resendChallenge,
  rotateRefresh,
  startSession,
  tenantOf,
  verifyChallenge,
} from '../core/auth'
import { actorOf, anonymousActor, recordAudit } from '../core/audit'
import { MockError, ok } from '../core/respond'
import { defineMockRoute } from '../core/route'
import { parseBody } from '../core/validate'
import { MOCK_TENANTS, MOCK_USERS, type MockTenant } from '../data/tenants'
import type { H3Event } from 'h3'
import type { Challenge, ChallengePurpose } from '../core/auth'

/** Verify a code and record a wrong / locked attempt in the audit trail before re-throwing. */
function verifyAudited(event: H3Event, id: string, code: string, purpose: ChallengePurpose): Challenge {
  const pending = getChallenge(id)
  try {
    return verifyChallenge(id, code, purpose)
  } catch (error) {
    if (error instanceof MockError && pending?.tenant) {
      const locked = error.code === 'FRM-AUTH-1004'
      recordAudit(event, pending.tenant, {
        action: locked ? 'auth.otp.locked' : 'auth.otp.failed',
        actor: pending.user ? actorOf(pending.user) : anonymousActor(pending.email),
        outcome: locked ? 'blocked' : 'failure',
        reason: error.code,
        metadata: {
          purpose,
          channel: pending.channel,
          ...(error.details[0] ? { attempts_left: error.details[0].message } : {}),
        },
      })
    }
    throw error
  }
}

const password = z
  .string()
  .min(10, 'At least 10 characters.')
  .regex(/[a-z]/, 'Add a lowercase letter.')
  .regex(/[A-Z]/, 'Add an uppercase letter.')
  .regex(/\d/, 'Add a number.')
const code = z.string().regex(/^\d{6}$/, 'Enter the 6-digit code.')

const loginSchema = z.object({ email: z.email(), password: z.string().min(1) })

/** POST /auth/login → OTP challenge (no tokens yet, SECURITY-PROTOCOL §7). */
export const login = defineMockRoute(({ event, body }) => {
  const tenant = requireTenant(event)
  if (!tenant.auth_providers.includes('password')) throw new MockError('FRM-AUTH-1008')
  const input = parseBody(loginSchema, body)
  const user = findUser(input.email, tenant.id)
  if (!user || user.password !== input.password) {
    recordAudit(event, tenant, {
      action: 'auth.login.failed',
      actor: user ? actorOf(user) : anonymousActor(input.email),
      outcome: 'failure',
      reason: 'FRM-AUTH-1002',
      metadata: { method: 'password', ...(user ? {} : { account: 'not_found' }) },
    })
    throw new MockError('FRM-AUTH-1002')
  }
  if (user.disabled) {
    recordAudit(event, tenant, {
      action: 'auth.login.blocked',
      actor: actorOf(user),
      outcome: 'blocked',
      severity: 'notice',
      reason: 'FRM-AUTH-1005',
      metadata: { method: 'password' },
    })
    throw new MockError('FRM-AUTH-1005')
  }
  const challenge = createChallenge({
    purpose: 'login',
    email: user.email,
    user,
    tenant,
    channel: 'email',
    channels: user.phone ? ['email', 'sms'] : ['email'],
  })
  recordAudit(event, tenant, {
    action: 'auth.otp.sent',
    actor: actorOf(user),
    metadata: { channel: 'email' },
  })
  return ok(describeChallenge(challenge), devMeta(challenge))
})

const verifySchema = z.object({ challenge_id: z.string(), code })

/** POST /auth/otp/verify — login → tokens + refresh cookie; signup → marks the email verified. */
export const verifyOtp = defineMockRoute(({ event, body }) => {
  const input = parseBody(verifySchema, body)
  const pending = getChallenge(input.challenge_id)
  if (pending?.purpose === 'signup') {
    verifyChallenge(input.challenge_id, input.code, 'signup')
    return ok({ verified: true })
  }
  const challenge = verifyAudited(event, input.challenge_id, input.code, 'login')
  consumeChallenge(challenge.id)
  recordAudit(event, challenge.tenant!, {
    action: 'auth.login.succeeded',
    actor: actorOf(challenge.user!),
    metadata: { method: 'password', channel: challenge.channel },
  })
  return ok(startSession(event, challenge.user!, challenge.tenant!))
})

const resendSchema = z.object({
  challenge_id: z.string(),
  channel: z.enum(['email', 'sms', 'totp']).optional(),
})

export const resendOtp = defineMockRoute(({ event, body }) => {
  const input = parseBody(resendSchema, body)
  const challenge = resendChallenge(input.challenge_id, input.channel)
  if (challenge.tenant)
    recordAudit(event, challenge.tenant, {
      action: 'auth.otp.sent',
      actor: challenge.user ? actorOf(challenge.user) : anonymousActor(challenge.email),
      metadata: { channel: challenge.channel, resend: String(challenge.resends) },
    })
  return ok(describeChallenge(challenge), devMeta(challenge))
})

export const refresh = defineMockRoute(({ event }) => ok(rotateRefresh(event)))

export const logout = defineMockRoute(({ event }) => {
  const session = endSession(event)
  if (session) recordAudit(event, session.tenant, { action: 'auth.logout', actor: actorOf(session.user) })
  return ok({ signed_out: true })
})

export const me = defineMockRoute(({ event }) => {
  const { user } = requireAuth(event)
  return ok({
    id: user.id,
    first_name: user.first_name,
    last_name: user.last_name,
    email: user.email,
    avatar_url: null,
    role: user.role,
  })
})

const signupSchema = z.object({
  first_name: z.string().trim().min(1).max(60),
  last_name: z.string().trim().min(1).max(60),
  email: z.email(),
  password,
})

/** POST /auth/signup (manage.* only) → OTP challenge to verify the email. */
export const signup = defineMockRoute(({ event, body }) => {
  if (tenantOf(event).context.kind !== 'manage') throw new MockError('FRM-PERM-1001')
  const input = parseBody(signupSchema, body)
  const challenge = createChallenge({
    purpose: 'signup',
    email: input.email,
    user: null,
    tenant: null,
    channel: 'email',
    channels: ['email'],
    signup: { first_name: input.first_name, last_name: input.last_name, password: input.password },
  })
  return ok(describeChallenge(challenge), devMeta(challenge))
})

const completeSchema = z.object({
  challenge_id: z.string(),
  company_name: z.string().trim().min(2).max(80),
  subdomain: z
    .string()
    .trim()
    .toLowerCase()
    .regex(/^[a-z0-9](?:[a-z0-9-]{1,61}[a-z0-9])$/),
})

/** POST /auth/signup/complete → creates tenant + organisation + admin; returns a ticket URL on the new subdomain. */
export const signupComplete = defineMockRoute(({ event, body }) => {
  const input = parseBody(completeSchema, body)
  const challenge = getChallenge(input.challenge_id)
  if (!challenge || challenge.purpose !== 'signup' || !challenge.verified || !challenge.signup) {
    throw new MockError('FRM-AUTH-1003')
  }
  if (MOCK_TENANTS.some(t => t.subdomain === input.subdomain)) {
    throw new MockError('FRM-TEN-1004', [{ field: 'subdomain', message: 'This subdomain is taken.' }])
  }
  const tenant: MockTenant = {
    id: crypto.randomUUID(),
    name: input.company_name,
    subdomain: input.subdomain,
    status: 'active',
    // New workspaces start with email + password; the admin enables more in Settings → Authentication (F12).
    // (Social signup will also enable the provider used — backend.)
    auth_providers: ['password'],
    organisation: { id: crypto.randomUUID(), name: input.company_name },
  }
  MOCK_TENANTS.push(tenant)
  const user = {
    id: crypto.randomUUID(),
    tenant_id: tenant.id,
    first_name: challenge.signup.first_name,
    last_name: challenge.signup.last_name,
    email: challenge.email,
    password: challenge.signup.password,
    phone: null,
    disabled: false,
    role: 'owner' as const,
  }
  MOCK_USERS.push(user)
  consumeChallenge(challenge.id)
  recordAudit(event, tenant, {
    action: 'workspace.created',
    actor: actorOf(user),
    resource: { type: 'workspace', id: tenant.id, name: tenant.name },
    metadata: { subdomain: tenant.subdomain },
  })
  const { public: config } = useRuntimeConfig(event)
  const port = getRequestURL(event).port
  const ticket = issueTicket(user, tenant)
  return ok<SignupComplete>({
    redirect_url: `https://${tenant.subdomain}.${config.rootDomain}${port ? `:${port}` : ''}/auth/welcome?ticket=${ticket}`,
  })
})

const ticketSchema = z.object({ ticket: z.string().min(10) })

/** POST /auth/exchange-ticket — one-time cross-subdomain hand-off → tokens + refresh cookie. */
export const exchangeTicket = defineMockRoute(({ event, body }) => {
  const { ticket } = parseBody(ticketSchema, body)
  const tokens = redeemTicket(event, ticket)
  const user = MOCK_USERS.find(item => item.id === tokens.user.id)
  if (user)
    recordAudit(event, requireTenant(event), {
      action: 'auth.login.succeeded',
      actor: actorOf(user),
      metadata: { method: 'signup_handoff' },
    })
  return ok(tokens)
})

const forgotSchema = z.object({ email: z.email() })

/** POST /auth/password/forgot — always answers the same (no account enumeration). */
export const forgotPassword = defineMockRoute(({ event, body }) => {
  const tenant = requireTenant(event)
  const { email } = parseBody(forgotSchema, body)
  const user = findUser(email, tenant.id)
  const challenge = createChallenge({
    purpose: 'reset',
    email,
    user,
    tenant,
    channel: 'email',
    channels: ['email'],
  })
  recordAudit(event, tenant, {
    action: 'auth.password.reset_requested',
    actor: user ? actorOf(user) : anonymousActor(email),
    outcome: user ? 'success' : 'failure',
    metadata: { channel: 'email', ...(user ? {} : { account: 'not_found' }) },
  })
  return ok(describeChallenge(challenge), devMeta(challenge))
})

const resetSchema = z.object({ challenge_id: z.string(), code, password })

export const resetPassword = defineMockRoute(({ event, body }) => {
  const input = parseBody(resetSchema, body)
  const challenge = verifyAudited(event, input.challenge_id, input.code, 'reset')
  consumeChallenge(challenge.id)
  if (challenge.user) {
    challenge.user.password = input.password
    recordAudit(event, challenge.tenant!, { action: 'auth.password.reset', actor: actorOf(challenge.user) })
  }
  return ok({ reset: true })
})

/** GET /auth/oauth/:provider/start — the mock has no identity providers configured. */
export const oauthStart = defineEventHandler(event => {
  const provider = getRouterParam(event, 'provider') ?? ''
  const page = getQuery(event).intent === 'signup' ? '/auth/signup' : '/auth/login'
  return sendRedirect(event, `${page}?oauth=unavailable&provider=${encodeURIComponent(provider)}`, 302)
})

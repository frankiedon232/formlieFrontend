import { z } from 'zod'
import type { SignupComplete } from '#shared/types/auth'
import { meetsPasswordPolicy, checkPassword } from '#shared/utils/auth/password'
import {
  callerIp,
  consumeChallenge,
  createChallenge,
  describeChallenge,
  devMeta,
  endSession,
  findUser,
  getChallenge,
  ipAllowed,
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
import { notify } from '../data/notificationStore'
import { sendEmail } from '../data/outboxStore'
import { settingsOf } from '../data/settingsStore'
import { peopleStoreOf, savePeople } from '../data/peopleStore'
import {
  hashPassword,
  MOCK_TENANTS,
  MOCK_USERS,
  passwordMatches,
  saveCreatedWorkspaces,
  type MockTenant,
  type MockUser,
} from '../data/tenants'
import type { H3Event } from 'h3'
import type { Challenge, ChallengePurpose } from '../core/auth'
import { grantsOf, permissionsOf, roleOf } from '../data/rolesStore'

/** Settings → Notifications: a blocked sign-in tells the admins (who, and why in words). */
const securityAlert = (event: H3Event, tenant: MockTenant, email: string, reason: string) => notify(event, tenant, 'security_alert', { email, reason }, '/audit?area=auth&outcome=failure,blocked')

/** The code email in the workspace's sent log (Settings → Email templates); the code itself is never kept there. */
function logCodeEmail(challenge: Challenge) {
  if (!challenge.tenant || challenge.channel !== 'email' || (challenge.purpose === 'reset' && !challenge.user)) return
  sendEmail(challenge.tenant, { to: challenge.email, key: challenge.purpose === 'reset' ? 'password_reset' : 'signin_code', vars: { name: challenge.user?.first_name ?? '', code: '••••••', minutes: Math.round(challenge.ttlMs / 60_000) }, reason: challenge.purpose })
}

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
      if (locked) securityAlert(event, pending.tenant, pending.email, 'code_locked')
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

/** Settings → Sign-in: an allowed email domain (or no list). */
function domainAllowed(tenant: MockTenant, email: string) {
  const domains = settingsOf(tenant).signin.allowed_domains
  const domain = email.split('@').pop()?.toLowerCase() ?? ''
  return !domains.length || domains.some(item => domain === item || domain.endsWith(`.${item}`))
}

/** Settings → Security: the password is older than the workspace allows. */
function passwordExpired(tenant: MockTenant, user: MockUser) {
  // An admin asked for a new one (People → Ask for a new password, F16 M3)
  if (user.must_change_password) return true
  const days = settingsOf(tenant).security.password.expiry_days
  return !!days && !!user.password_changed_at && Date.now() - Date.parse(user.password_changed_at) > days * 86_400_000
}

/** POST /auth/login → OTP challenge (no tokens yet, SECURITY-PROTOCOL §7). */
export const login = defineMockRoute(({ event, body }) => {
  const tenant = requireTenant(event)
  const { signin } = settingsOf(tenant)
  if (!signin.methods.includes('password')) throw new MockError('FRM-AUTH-1008')
  const input = parseBody(loginSchema, body)
  // Settings → Security: only from the allowed networks (checked first, says nothing about the account)
  if (!ipAllowed(tenant, callerIp(event))) {
    recordAudit(event, tenant, { action: 'auth.login.blocked', actor: anonymousActor(input.email), outcome: 'blocked', reason: 'FRM-AUTH-1016', metadata: { method: 'password', cause: 'ip_not_allowed' } })
    securityAlert(event, tenant, input.email, 'ip_not_allowed')
    throw new MockError('FRM-AUTH-1016')
  }
  const user = findUser(input.email, tenant.id)
  if (!user || !passwordMatches(user, input.password)) {
    recordAudit(event, tenant, {
      action: 'auth.login.failed',
      actor: user ? actorOf(user) : anonymousActor(input.email),
      outcome: 'failure',
      reason: 'FRM-AUTH-1002',
      metadata: { method: 'password', ...(user ? {} : { account: 'not_found' }) },
    })
    throw new MockError('FRM-AUTH-1002')
  }
  // Signed up with a link: not until an admin approves (F16 R3)
  if (user.awaiting_approval) {
    recordAudit(event, tenant, { action: 'auth.login.blocked', actor: actorOf(user), outcome: 'blocked', severity: 'notice', reason: 'FRM-USER-1010', metadata: { method: 'password', cause: 'awaiting_approval' } })
    throw new MockError('FRM-USER-1010')
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
    securityAlert(event, tenant, user.email, 'account_disabled')
    throw new MockError('FRM-AUTH-1005')
  }
  if (!domainAllowed(tenant, user.email)) {
    recordAudit(event, tenant, { action: 'auth.login.blocked', actor: actorOf(user), outcome: 'blocked', severity: 'notice', reason: 'FRM-AUTH-1014', metadata: { method: 'password', cause: 'email_domain' } })
    securityAlert(event, tenant, user.email, 'email_domain')
    throw new MockError('FRM-AUTH-1014')
  }
  if (passwordExpired(tenant, user)) {
    recordAudit(event, tenant, { action: 'auth.login.blocked', actor: actorOf(user), outcome: 'blocked', severity: 'notice', reason: 'FRM-AUTH-1015', metadata: { method: 'password', cause: 'password_expired' } })
    throw new MockError('FRM-AUTH-1015')
  }
  const challenge = createChallenge({
    purpose: 'login',
    email: user.email,
    user,
    tenant,
    // An authenticator app comes first when they set one up (My profile, F16 M5); no code is sent then
    channel: user.totp_secret ? 'totp' : 'email',
    // Text messages only when the workspace allows them (Settings → Sign-in)
    channels: [...(user.totp_secret ? (['totp'] as const) : []), 'email', ...(user.phone && signin.code.sms ? (['sms'] as const) : [])],
  })
  recordAudit(event, tenant, {
    action: 'auth.otp.sent',
    actor: actorOf(user),
    metadata: { channel: challenge.channel },
  })
  logCodeEmail(challenge)
  return ok(describeChallenge(challenge), challenge.channel === 'totp' ? {} : devMeta(challenge))
})

// A recovery code ("k7q2-9xmd") also passes where an authenticator code is asked (F16 M5)
const verifySchema = z.object({ challenge_id: z.string(), code: z.union([code, z.string().trim().regex(/^[a-z0-9]{4}-?[a-z0-9]{4}$/i)]) })

/** POST /auth/otp/verify, login → tokens + refresh cookie; signup → marks the email verified. */
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
  logCodeEmail(challenge)
  return ok(describeChallenge(challenge), devMeta(challenge))
})

export const refresh = defineMockRoute(({ event }) => ok(rotateRefresh(event)))

export const logout = defineMockRoute(({ event }) => {
  const session = endSession(event)
  if (session) recordAudit(event, session.tenant, { action: 'auth.logout', actor: actorOf(session.user) })
  return ok({ signed_out: true })
})

export const me = defineMockRoute(({ event }) => {
  const { user, tenant } = requireAuth(event)
  return ok({
    id: user.id,
    first_name: user.first_name,
    last_name: user.last_name,
    email: user.email,
    avatar_url: user.photo ?? null,
    role: user.role,
    role_name: roleOf(tenant, user.role)?.name ?? user.role,
    permissions: [...permissionsOf(user, tenant)],
      grants: grantsOf(user, tenant),
    language: user.language ?? null,
    time_zone: user.time_zone ?? null,
    date_format: user.date_format ?? null,
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
    // New workspaces start with email + password; the admin enables more in Settings → Authentication (F14).
    // (Social signup will also enable the provider used, backend.)
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
  saveCreatedWorkspaces()
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

/** POST /auth/exchange-ticket, one-time cross-subdomain hand-off → tokens + refresh cookie. */
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

/** POST /auth/password/forgot, always answers the same (no account enumeration). */
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
  logCodeEmail(challenge)
  return ok(describeChallenge(challenge), devMeta(challenge))
})

const resetSchema = z.object({ challenge_id: z.string(), code, password: z.string().min(1).max(200) })

/** The workspace's password rules (Settings → Security): FRM-AUTH-1007 names what is missing, 1018 a recent one. */
export function checkNewPassword(tenant: MockTenant, user: MockUser | null, value: string) {
  const rules = settingsOf(tenant).security.password
  if (!meetsPasswordPolicy(value, rules)) {
    const missing = checkPassword(value, rules).filter(check => check.required && !check.passed)
    throw new MockError('FRM-AUTH-1007', missing.map(check => ({ field: 'password', message: check.key === 'length' ? `min_length:${rules.min_length}` : check.key })))
  }
  if (user && rules.reuse_last) {
    const hash = hashPassword(value)
    if (passwordMatches(user, value) || (user.password_history ?? []).slice(0, rules.reuse_last - 1).includes(hash)) throw new MockError('FRM-AUTH-1018', [{ field: 'password', message: `last_${rules.reuse_last}` }])
  }
}

export const resetPassword = defineMockRoute(({ event, body }) => {
  const input = parseBody(resetSchema, body)
  const pending = getChallenge(input.challenge_id)
  // The rules first, so a refused password doesn't use up the code
  if (pending?.purpose === 'reset' && pending.tenant) checkNewPassword(pending.tenant, pending.user, input.password)
  const challenge = verifyAudited(event, input.challenge_id, input.code, 'reset')
  consumeChallenge(challenge.id)
  if (challenge.user) {
    const old = challenge.user.password.startsWith('sha256:') ? challenge.user.password : hashPassword(challenge.user.password)
    challenge.user.password_history = [old, ...(challenge.user.password_history ?? [])].slice(0, 10)
    challenge.user.password = input.password
    challenge.user.password_changed_at = new Date().toISOString()
    if (challenge.user.must_change_password) {
      challenge.user.must_change_password = false
      const person = challenge.tenant ? peopleStoreOf(challenge.tenant).find(item => item.id === challenge.user!.id) : undefined
      if (person) {
        delete person.must_change_password
        savePeople()
      }
    }
    saveCreatedWorkspaces()
    recordAudit(event, challenge.tenant!, { action: 'auth.password.reset', actor: actorOf(challenge.user) })
  }
  return ok({ reset: true })
})

/** GET /auth/oauth/:provider/start, the mock has no identity providers configured. */
export const oauthStart = defineEventHandler(event => {
  const provider = getRouterParam(event, 'provider') ?? ''
  const page = getQuery(event).intent === 'signup' ? '/auth/signup' : '/auth/login'
  return sendRedirect(event, `${page}?oauth=unavailable&provider=${encodeURIComponent(provider)}`, 302)
})

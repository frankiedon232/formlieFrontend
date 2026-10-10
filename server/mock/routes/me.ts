/**
 * My profile (F16 M5, docs/API-CONTRACT.md → My profile): every signed-in person, about themselves.
 *
 *   GET    /me/profile                         MyProfile
 *   PATCH  /me/profile                         { first_name?, last_name?, photo?, language?, time_zone?, date_format?, notifications? }
 *   POST   /me/password                        { current, password } (the workspace's password rules)
 *   POST   /me/two-step/app                    → { secret, uri } to scan; confirmed by
 *   POST   /me/two-step/app/confirm            { code } → { recovery_codes } (shown once)
 *   POST   /me/two-step/app/remove             { password }
 *   POST   /me/two-step/recovery               { password } → { recovery_codes } (the old ones stop working)
 *   POST   /me/two-step/phone                  { phone } → a code by text message (dev: meta.dev_code)
 *   POST   /me/two-step/phone/confirm          { code } → the number takes SMS codes
 *   DELETE /me/two-step/phone
 *   GET    /me/sessions · DELETE /me/sessions/:id · POST /me/sessions/sign-out-others
 */
import { z } from 'zod'
import type { MyProfile, MySession, ProfileNotification } from '#shared/types/profile'
import { PROFILE_DATE_FORMATS, PROFILE_NOTIFICATIONS } from '#shared/types/profile'
import type { AuditAction } from '#shared/utils/audit/events'
import type { MyTours } from '#shared/types/help'
import { actorOf, recordAudit } from '../core/audit'
import { activeSessions, currentSessionId, requireAuth, revokeSessions } from '../core/auth'
import { MockError, ok } from '../core/respond'
import { defineMockRoute } from '../core/route'
import { newRecoveryCodes, newSecret, otpauthUri, verifyTotp } from '../core/totp'
import { parseBody } from '../core/validate'
import { peopleRows, peopleStoreOf, savePeople, type StoredPerson } from '../data/peopleStore'
import { settingsOf } from '../data/settingsStore'
import { hashPassword, passwordMatches, saveCreatedWorkspaces, type MockTenant, type MockUser } from '../data/tenants'
import { checkNewPassword } from './auth'
import type { H3Event } from 'h3'

const NOTIFY_DEFAULTS: Record<ProfileNotification, boolean> = { responses: true, digest: false, mentions: true, product: false }
/** "+44 •••• ••0001": the country code and the last four digits. */
const mask = (phone: string) => {
  const digits = phone.replace(/\D/g, '')
  return `+${digits.slice(0, 2)} ${'•'.repeat(Math.max(0, digits.length - 6))}${digits.slice(-4)}`
}

/** The person and their account; profile changes go to both (the account signs in, the person is saved). */
function mine(event: H3Event) {
  const { user, tenant } = requireAuth(event)
  const person = peopleStoreOf(tenant).find(item => item.id === user.id)
  if (!person) throw new MockError('FRM-GEN-1004')
  return { user, tenant, person }
}
function put(user: MockUser, person: StoredPerson, values: Partial<MockUser & StoredPerson>) {
  const { password: _password, password_hash, ...rest } = values
  Object.assign(user, rest)
  Object.assign(person, rest, password_hash ? { password_hash } : {})
  savePeople()
  saveCreatedWorkspaces()
}
const audit = (event: H3Event, tenant: MockTenant, user: MockUser, action: AuditAction, metadata: Record<string, string> = {}) =>
  recordAudit(event, tenant, { action, actor: actorOf(user), resource: { type: 'user', id: user.id, name: `${user.first_name} ${user.last_name}`.trim() }, metadata })

function profileOf(tenant: MockTenant, user: MockUser, person: StoredPerson): MyProfile {
  const row = peopleRows(tenant).find(item => item.id === user.id)
  return {
    id: user.id,
    first_name: user.first_name,
    last_name: user.last_name,
    email: user.email,
    photo: user.photo ?? null,
    language: user.language ?? null,
    time_zone: user.time_zone ?? null,
    date_format: user.date_format ?? null,
    role: user.role,
    role_name: row?.role_name ?? user.role,
    departments: row?.departments ?? [],
    job_titles: row?.job_titles ?? [],
    manager: row?.manager ?? null,
    password_changed_at: user.password_changed_at ?? null,
    two_step: { app: !!user.totp_secret, recovery_left: user.recovery_hashes?.length ?? 0, phone: user.phone ? mask(user.phone) : null, sms_allowed: settingsOf(tenant).signin.code.sms },
    notifications: { ...NOTIFY_DEFAULTS, ...(person.notifications ?? {}) } as Record<ProfileNotification, boolean>,
  }
}
/** Two-step sign-in is on when an app or a number is set (the People page shows it). */
const twoStepOf = (user: MockUser) => !!user.totp_secret || !!user.phone

export const getProfile = defineMockRoute(({ event }) => {
  const { user, tenant, person } = mine(event)
  return ok(profileOf(tenant, user, person))
})

const photo = z
  .string()
  .max(280_000)
  .regex(/^data:image\/(png|jpeg|webp);base64,[A-Za-z0-9+/=]+$/)
const profileBody = z.object({
  first_name: z.string().trim().min(1).max(60).optional(),
  last_name: z.string().trim().min(1).max(60).optional(),
  photo: photo.nullable().optional(),
  language: z.string().max(10).nullable().optional(),
  time_zone: z.string().max(64).refine(value => { try { new Intl.DateTimeFormat('en', { timeZone: value }); return true } catch { return false } }).nullable().optional(),
  date_format: z.enum(PROFILE_DATE_FORMATS).nullable().optional(),
  notifications: z.object(Object.fromEntries(PROFILE_NOTIFICATIONS.map(key => [key, z.boolean()]))).partial().optional(),
})

export const updateProfile = defineMockRoute(({ event, body }) => {
  const { user, tenant, person } = mine(event)
  const input = parseBody(profileBody, body)
  const { notifications, ...rest } = input
  const values = Object.fromEntries(Object.entries(rest).filter(([, value]) => value !== undefined))
  put(user, person, values)
  if (notifications) {
    person.notifications = { ...(person.notifications ?? {}), ...(notifications as Record<string, boolean>) }
    savePeople()
  }
  audit(event, tenant, user, 'users.profile_updated', { fields: [...Object.keys(values), ...(notifications ? ['notifications'] : [])].join(', ') })
  return ok(profileOf(tenant, user, person))
})

const passwordBody = z.object({ current: z.string().min(1).max(200), password: z.string().min(1).max(200) })
export const changePassword = defineMockRoute(({ event, body }) => {
  const { user, tenant, person } = mine(event)
  const input = parseBody(passwordBody, body)
  if (!passwordMatches(user, input.current)) throw new MockError('FRM-AUTH-1001', [{ field: 'current', message: 'wrong' }])
  checkNewPassword(tenant, user, input.password)
  const old = user.password.startsWith('sha256:') ? user.password : hashPassword(user.password)
  user.password_history = [old, ...(user.password_history ?? [])].slice(0, 10)
  // The account takes the password; the saved person keeps only its hash (never the typed password)
  Object.assign(user, { password: input.password, password_changed_at: new Date().toISOString(), must_change_password: false })
  put(user, person, { password_hash: hashPassword(input.password), must_change_password: false })
  // Other devices sign in again with the new password
  revokeSessions(tenant, { ids: activeSessions(event, tenant).filter(item => item.user.email === user.email && !item.current).map(item => item.id) })
  audit(event, tenant, user, 'auth.password.changed')
  return ok({ changed: true })
})

// ── Two-step sign-in ─────────────────────────────────────────────────────────────────

const pendingSecrets = new Map<string, { secret: string; at: number }>()
const pendingPhones = new Map<string, { phone: string; code: string; at: number }>()

export const startApp = defineMockRoute(({ event }) => {
  const { user, tenant } = mine(event)
  const secret = newSecret()
  pendingSecrets.set(user.id, { secret, at: Date.now() })
  return ok({ secret, uri: otpauthUri(secret, user.email, tenant.name ? `Formalie (${tenant.name})` : 'Formalie') })
})

const codeBody = z.object({ code: z.string().trim().regex(/^\d{6}$/) })
export const confirmApp = defineMockRoute(({ event, body }) => {
  const { user, tenant, person } = mine(event)
  const { code } = parseBody(codeBody, body)
  const pending = pendingSecrets.get(user.id)
  if (!pending || Date.now() - pending.at > 15 * 60_000) throw new MockError('FRM-AUTH-1003')
  if (!verifyTotp(pending.secret, code)) throw new MockError('FRM-AUTH-1003')
  pendingSecrets.delete(user.id)
  const recovery = newRecoveryCodes()
  put(user, person, { totp_secret: pending.secret, recovery_hashes: recovery.hashes })
  put(user, person, { two_step: twoStepOf(user) } as Partial<StoredPerson>)
  audit(event, tenant, user, 'auth.two_step.enabled', { method: 'app' })
  return ok({ recovery_codes: recovery.codes })
})

const passwordOnly = z.object({ password: z.string().min(1).max(200) })
function confirmPassword(user: MockUser, body: unknown) {
  const { password } = parseBody(passwordOnly, body)
  if (!passwordMatches(user, password)) throw new MockError('FRM-AUTH-1001', [{ field: 'password', message: 'wrong' }])
}
export const removeApp = defineMockRoute(({ event, body }) => {
  const { user, tenant, person } = mine(event)
  confirmPassword(user, body)
  put(user, person, { totp_secret: null, recovery_hashes: [] })
  put(user, person, { two_step: twoStepOf(user) } as Partial<StoredPerson>)
  audit(event, tenant, user, 'auth.two_step.disabled', { method: 'app' })
  return ok(profileOf(tenant, user, person))
})
export const newRecovery = defineMockRoute(({ event, body }) => {
  const { user, tenant, person } = mine(event)
  confirmPassword(user, body)
  if (!user.totp_secret) throw new MockError('FRM-GEN-1004')
  const recovery = newRecoveryCodes()
  put(user, person, { recovery_hashes: recovery.hashes })
  audit(event, tenant, user, 'auth.recovery_codes.created')
  return ok({ recovery_codes: recovery.codes })
})

const phoneBody = z.object({ phone: z.string().trim().regex(/^\+[1-9][\d\s-]{6,18}$/) })
export const startPhone = defineMockRoute(({ event, body }) => {
  const { user, tenant } = mine(event)
  if (!settingsOf(tenant).signin.code.sms) throw new MockError('FRM-GEN-1002', [{ field: 'phone', message: 'sms_off' }])
  const { phone } = parseBody(phoneBody, body)
  const code = String(Math.floor(100000 + Math.random() * 900000))
  pendingPhones.set(user.id, { phone: phone.replace(/[\s-]/g, ''), code, at: Date.now() })
  console.info(`[mock-otp] phone code for ${user.email}: ${code}`)
  return ok({ masked: mask(phone) }, { dev_code: code })
})
export const confirmPhone = defineMockRoute(({ event, body }) => {
  const { user, tenant, person } = mine(event)
  const { code } = parseBody(codeBody, body)
  const pending = pendingPhones.get(user.id)
  if (!pending || Date.now() - pending.at > 10 * 60_000 || pending.code !== code) throw new MockError('FRM-AUTH-1003')
  pendingPhones.delete(user.id)
  put(user, person, { phone: pending.phone })
  put(user, person, { two_step: twoStepOf(user) } as Partial<StoredPerson>)
  audit(event, tenant, user, 'auth.two_step.enabled', { method: 'sms' })
  return ok(profileOf(tenant, user, person))
})
export const removePhone = defineMockRoute(({ event }) => {
  const { user, tenant, person } = mine(event)
  put(user, person, { phone: null })
  put(user, person, { two_step: twoStepOf(user) } as Partial<StoredPerson>)
  audit(event, tenant, user, 'auth.two_step.disabled', { method: 'sms' })
  return ok(profileOf(tenant, user, person))
})

// ── Sessions ─────────────────────────────────────────────────────────────────────────

const sessionsOf = (event: H3Event, tenant: MockTenant, user: MockUser): MySession[] =>
  activeSessions(event, tenant)
    .filter(item => item.user.email === user.email)
    .map(item => ({ id: item.id, current: item.current, started_at: item.started_at, last_active_at: item.last_active_at, ip: item.ip, device: item.device }))

export const mySessions = defineMockRoute(({ event }) => {
  const { user, tenant } = requireAuth(event)
  return ok(sessionsOf(event, tenant, user))
})
export const endMySession = defineMockRoute(({ event }) => {
  const { user, tenant } = requireAuth(event)
  const id = getRouterParam(event, 'id') ?? ''
  if (!sessionsOf(event, tenant, user).some(item => item.id === id)) throw new MockError('FRM-GEN-1004')
  if (id === currentSessionId(event)) throw new MockError('FRM-USER-1005')
  revokeSessions(tenant, { ids: [id] })
  audit(event, tenant, user, 'auth.session.revoked', { sessions: '1' })
  return ok(sessionsOf(event, tenant, user))
})
export const endOtherSessions = defineMockRoute(({ event }) => {
  const { user, tenant } = requireAuth(event)
  const ids = sessionsOf(event, tenant, user).filter(item => !item.current).map(item => item.id)
  if (ids.length) revokeSessions(tenant, { ids })
  audit(event, tenant, user, 'auth.session.revoked', { sessions: String(ids.length) })
  return ok(sessionsOf(event, tenant, user))
})

// ── Tips on new pages (first-visit tours) ─────────────────────────────────────────────────
const toursOf = (person: StoredPerson): MyTours => ({ enabled: !person.tours?.off, seen: person.tours?.seen ?? [] })

/** GET /me/tours */
export const myTours = defineMockRoute(({ event }) => ok(toursOf(mine(event).person)))

const toursBody = z.object({
  /** A tour offered (taken or skipped): not offered again. */
  seen: z.string().trim().min(1).max(60).optional(),
  enabled: z.boolean().optional(),
  /** "Show all tips again". */
  reset: z.literal(true).optional(),
})
/** PATCH /me/tours */
export const updateMyTours = defineMockRoute(({ event, body }) => {
  const { person } = mine(event)
  const input = parseBody(toursBody, body)
  const tours = { off: person.tours?.off, seen: [...(person.tours?.seen ?? [])] }
  if (input.enabled !== undefined) tours.off = !input.enabled
  if (input.reset) tours.seen = []
  if (input.seen && !tours.seen.includes(input.seen)) tours.seen.push(input.seen)
  person.tours = { ...(tours.off ? { off: true } : {}), seen: tours.seen.slice(-100) }
  savePeople()
  return ok(toursOf(person))
})

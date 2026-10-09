/**
 * Ways into a workspace (F16 rework, owner 2026-10-09; docs/API-CONTRACT.md → People):
 * - **User profiles**: an admin makes the full profile (name, email, role, departments, job titles,
 *   manager); the person gets an activation email, sets their password and signs in (not_activated → active).
 * - **Personal sign-up links**: sent to chosen addresses; the person signs up and then **waits for
 *   approval** (invited → pending).
 * - **The workspace's shared link** (signupLinkStore): anyone with it asks to join (domains optional),
 *   then waits for approval (pending).
 * - **Approval**: approve (completing the profile: role, departments, job titles, manager) or reject.
 * Links work 7 days (the shared one until turned off or renewed); only a hash of personal tokens is kept.
 *
 *   POST   /people                          create a user profile (activation email)
 *   POST   /people/invites                  personal sign-up links
 *   POST   /people/:id/invite/resend · /invite/link · DELETE /people/:id/invite
 *   GET · PUT /people/signup-link · POST /people/signup-link/new
 *   POST   /people/:id/approve · /reject
 *   GET    /public/invites/:token           what the sign-up page shows
 *   POST   /public/invites/:token/accept    { first_name, last_name, email?, phone?, password }
 */
import { createHash, randomBytes } from 'node:crypto'
import type { H3Event } from 'h3'
import { z } from 'zod'
import type { InvitePreview, InviteResult } from '#shared/types/people'
import type { AuditAction } from '#shared/utils/audit/events'
import { actorOf, recordAudit } from '../core/audit'
import { requireAdmin, tenantOf } from '../core/auth'
import { MockError, ok } from '../core/respond'
import { defineMockRoute } from '../core/route'
import { parseBody } from '../core/validate'
import { sendEmail } from '../data/outboxStore'
import { orgOf, saveOrg } from '../data/orgStore'
import { peopleStoreOf, personDetail, savePeople, type StoredPerson } from '../data/peopleStore'
import { roleOf } from '../data/rolesStore'
import { newSignupToken, saveSignupLinks, signupLinkOf, tenantBySignupToken } from '../data/signupLinkStore'
import { hashPassword, MOCK_TENANTS, MOCK_USERS, saveCreatedWorkspaces, type MockTenant, type MockUser } from '../data/tenants'
import { checkNewPassword } from './auth'

const DAYS = 7
const hash = (token: string) => createHash('sha256').update(token).digest('hex')
const nameOf = (user: { first_name: string; last_name: string }) => `${user.first_name} ${user.last_name}`.trim()

/** The workspace's own address; on a dev host without one (localhost) the tenant rides along. */
function linkTo(event: H3Event, tenant: MockTenant, token: string) {
  const url = getRequestURL(event, { xForwardedHost: true })
  const local = !url.hostname.includes(tenant.subdomain ?? '\u0000')
  return `${url.origin}/auth/join/${token}${local ? `?tenant=${tenant.subdomain}` : ''}`
}
/** A new personal link (activation or sign-up); the old one stops working. */
function freshLink(event: H3Event, tenant: MockTenant, person: StoredPerson, by: MockUser, message: string | null): string {
  const token = randomBytes(24).toString('base64url')
  const now = new Date()
  person.invite = { kind: person.status === 'not_activated' ? 'activation' : 'invite', token_hash: hash(token), sent_at: now.toISOString(), expires_at: new Date(now.getTime() + DAYS * 86_400_000).toISOString(), invited_by: { id: by.id, name: nameOf(by) }, message }
  return linkTo(event, tenant, token)
}
function mail(tenant: MockTenant, person: StoredPerson, by: MockUser, link: string) {
  // A profile the organisation made: activate it (set a password); a sign-up link: the invitation email
  if (person.status === 'not_activated') {
    const message = `${nameOf(by)} made your profile at ${tenant.name}. Open the link within ${DAYS} days to choose your password, then sign in.`
    return sendEmail(tenant, { to: person.email, key: 'notification', vars: { title: `Activate your account at ${tenant.name}`, message, link, workspace: tenant.name }, reason: 'invitation' })
  }
  sendEmail(tenant, { to: person.email, key: 'invitation', vars: { name: person.first_name || person.email, inviter: nameOf(by), workspace: tenant.name, link }, reason: 'invitation' })
}
const linkOut = (tenant: MockTenant, id: string | undefined) => {
  const person = peopleStoreOf(tenant).find(item => item.id === id)
  if (!person || (person.status !== 'invited' && person.status !== 'not_activated')) throw new MockError('FRM-GEN-1004')
  return person
}
const audit = (event: H3Event, tenant: MockTenant, user: MockUser, action: AuditAction, person: StoredPerson, metadata: Record<string, string> = {}) =>
  recordAudit(event, tenant, { action, actor: actorOf(user), resource: { type: 'user', id: person.id, name: nameOf(person) || person.email }, metadata })
/** Departments and job titles live in the organisation data, so Settings and People agree. */
function joinOrg(tenant: MockTenant, person: StoredPerson, departments: string[], jobs: string[]) {
  const org = orgOf(tenant)
  for (const [items, ids] of [[org.departments, departments], [org.job_titles, jobs]] as const)
    for (const item of items) {
      const wanted = ids.includes(item.id) && !item.archived_at
      if (wanted && !item.member_ids.includes(person.id)) item.member_ids.push(person.id)
      if (!wanted && !item.archived_at) item.member_ids = item.member_ids.filter(id => id !== person.id)
    }
}
const assertRole = (tenant: MockTenant, role: string) => {
  if (role === 'owner' || !roleOf(tenant, role)) throw new MockError('FRM-USER-1009')
}

// ── User profiles (admins) ───────────────────────────────────────────────────────────

const profileBody = z.object({
  first_name: z.string().trim().min(1).max(60),
  last_name: z.string().trim().min(1).max(60),
  email: z.email().max(200),
  phone: z.string().trim().regex(/^\+[1-9][\d\s-]{6,18}$/).nullable().optional(),
  role: z.string().min(1).max(64),
  department_ids: z.array(z.string().max(64)).max(20).default([]),
  job_title_ids: z.array(z.string().max(64)).max(20).default([]),
  manager_id: z.string().max(64).nullable().optional(),
})

export const createProfile = defineMockRoute(({ event, body }) => {
  const { user, tenant } = requireAdmin(event)
  const input = parseBody(profileBody, body)
  assertRole(tenant, input.role)
  const email = input.email.trim().toLowerCase()
  const people = peopleStoreOf(tenant)
  if (people.some(item => item.email.toLowerCase() === email)) throw new MockError('FRM-USER-1011')
  const person: StoredPerson = { id: crypto.randomUUID(), first_name: input.first_name, last_name: input.last_name, email, phone: input.phone?.replace(/[\s-]/g, '') ?? null, role: input.role, status: 'not_activated', manager_id: input.manager_id && people.some(item => item.id === input.manager_id) ? input.manager_id : null, two_step: false, joined_at: new Date().toISOString() }
  people.push(person)
  joinOrg(tenant, person, input.department_ids, input.job_title_ids)
  mail(tenant, person, user, freshLink(event, tenant, person, user, null))
  savePeople()
  saveOrg()
  audit(event, tenant, user, 'users.profile_created', person, { role: input.role })
  return ok(personDetail(tenant, person.id), {}, 201)
})

// ── Personal sign-up links ───────────────────────────────────────────────────────────

const inviteBody = z.object({
  emails: z.array(z.email().max(200)).min(1).max(50),
  role: z.string().min(1).max(64),
  department_ids: z.array(z.string().max(64)).max(20).default([]),
  job_title_ids: z.array(z.string().max(64)).max(20).default([]),
  message: z.string().trim().max(500).nullable().optional(),
})

export const invitePeople = defineMockRoute(({ event, body }) => {
  const { user, tenant } = requireAdmin(event)
  const input = parseBody(inviteBody, body)
  assertRole(tenant, input.role)
  const people = peopleStoreOf(tenant)
  const result: InviteResult = { invited: 0, skipped: [] }
  for (const email of [...new Set(input.emails.map(item => item.trim().toLowerCase()))]) {
    const existing = people.find(item => item.email.toLowerCase() === email)
    if (existing) {
      result.skipped.push({ email, reason: existing.status === 'invited' ? 'invited' : 'member' })
      continue
    }
    // The role, departments and job titles are a starting point: they are confirmed when approved
    const person: StoredPerson = { id: crypto.randomUUID(), first_name: '', last_name: '', email, phone: null, role: input.role, status: 'invited', manager_id: null, two_step: false, joined_at: new Date().toISOString() }
    people.push(person)
    joinOrg(tenant, person, input.department_ids, input.job_title_ids)
    mail(tenant, person, user, freshLink(event, tenant, person, user, input.message ?? null))
    audit(event, tenant, user, 'users.invited', person, { role: input.role })
    result.invited++
  }
  savePeople()
  saveOrg()
  return ok(result, {}, 201)
})

export const resendInvite = defineMockRoute(({ event }) => {
  const { user, tenant } = requireAdmin(event)
  const person = linkOut(tenant, getRouterParam(event, 'id'))
  mail(tenant, person, user, freshLink(event, tenant, person, user, person.invite?.message ?? null))
  savePeople()
  audit(event, tenant, user, 'users.invite_resent', person)
  return ok({ expires_at: person.invite!.expires_at })
})

export const inviteLink = defineMockRoute(({ event }) => {
  const { user, tenant } = requireAdmin(event)
  const person = linkOut(tenant, getRouterParam(event, 'id'))
  const link = freshLink(event, tenant, person, user, person.invite?.message ?? null)
  savePeople()
  audit(event, tenant, user, 'users.invite_link', person)
  return ok({ link, expires_at: person.invite!.expires_at })
})

/** Withdraws a personal link or an unactivated profile: the person and their memberships go. */
function removePerson(tenant: MockTenant, person: StoredPerson) {
  const people = peopleStoreOf(tenant)
  people.splice(people.indexOf(person), 1)
  const org = orgOf(tenant)
  for (const item of [...org.departments, ...org.job_titles]) item.member_ids = item.member_ids.filter(id => id !== person.id)
  const account = MOCK_USERS.findIndex(item => item.id === person.id)
  if (account >= 0) MOCK_USERS.splice(account, 1)
  savePeople()
  saveOrg()
  saveCreatedWorkspaces()
}

export const revokeInvite = defineMockRoute(({ event }) => {
  const { user, tenant } = requireAdmin(event)
  const person = linkOut(tenant, getRouterParam(event, 'id'))
  removePerson(tenant, person)
  audit(event, tenant, user, 'users.invite_revoked', person)
  return ok({ id: person.id })
})

// ── The workspace's shared link ──────────────────────────────────────────────────────

const linkView = (event: H3Event, tenant: MockTenant) => {
  const link = signupLinkOf(tenant)
  return { enabled: link.enabled, link: linkTo(event, tenant, link.token), domains: link.domains, updated_at: link.updated_at, pending: peopleStoreOf(tenant).filter(item => item.status === 'pending').length }
}
export const getSignupLink = defineMockRoute(({ event }) => {
  const { tenant } = requireAdmin(event)
  return ok(linkView(event, tenant))
})
const linkBody = z.object({ enabled: z.boolean().optional(), domains: z.array(z.string().trim().toLowerCase().regex(/^[a-z0-9-]+(\.[a-z0-9-]+)+$/)).max(20).optional() })
export const updateSignupLink = defineMockRoute(({ event, body }) => {
  const { user, tenant } = requireAdmin(event)
  const input = parseBody(linkBody, body)
  const link = signupLinkOf(tenant)
  Object.assign(link, { ...(input.enabled !== undefined ? { enabled: input.enabled } : {}), ...(input.domains ? { domains: [...new Set(input.domains)] } : {}), updated_at: new Date().toISOString() })
  saveSignupLinks()
  recordAudit(event, tenant, { action: 'users.signup_link_changed', actor: actorOf(user), metadata: { enabled: String(link.enabled), domains: link.domains.join(', ') || 'any' } })
  return ok(linkView(event, tenant))
})
export const renewSignupLink = defineMockRoute(({ event }) => {
  const { user, tenant } = requireAdmin(event)
  const link = signupLinkOf(tenant)
  Object.assign(link, { token: newSignupToken(), updated_at: new Date().toISOString() })
  saveSignupLinks()
  recordAudit(event, tenant, { action: 'users.signup_link_changed', actor: actorOf(user), metadata: { renewed: 'true' } })
  return ok(linkView(event, tenant))
})

// ── Approval ─────────────────────────────────────────────────────────────────────────

const approveBody = z.object({ role: z.string().min(1).max(64), department_ids: z.array(z.string().max(64)).max(20).default([]), job_title_ids: z.array(z.string().max(64)).max(20).default([]), manager_id: z.string().max(64).nullable().optional() })
const pendingOf = (tenant: MockTenant, id: string | undefined) => {
  const person = peopleStoreOf(tenant).find(item => item.id === id)
  if (!person || person.status !== 'pending') throw new MockError('FRM-GEN-1004')
  return person
}

export const approvePerson = defineMockRoute(({ event, body }) => {
  const { user, tenant } = requireAdmin(event)
  const person = pendingOf(tenant, getRouterParam(event, 'id'))
  const input = parseBody(approveBody, body)
  assertRole(tenant, input.role)
  Object.assign(person, { role: input.role, status: 'active', manager_id: input.manager_id ?? null, joined_at: new Date().toISOString() })
  delete person.request
  joinOrg(tenant, person, input.department_ids, input.job_title_ids)
  const account = MOCK_USERS.find(item => item.id === person.id)
  if (account) Object.assign(account, { role: input.role, awaiting_approval: false })
  savePeople()
  saveOrg()
  saveCreatedWorkspaces()
  const url = getRequestURL(event, { xForwardedHost: true })
  sendEmail(tenant, { to: person.email, key: 'notification', vars: { title: `You can sign in to ${tenant.name}`, message: `${nameOf(user)} approved your account. Sign in with your email address and password.`, link: `${url.origin}/auth/login`, workspace: tenant.name }, reason: 'approval' })
  audit(event, tenant, user, 'users.approved', person, { role: input.role })
  return ok(personDetail(tenant, person.id))
})

const rejectBody = z.object({ reason: z.string().trim().max(500).nullable().optional() })
export const rejectPerson = defineMockRoute(({ event, body }) => {
  const { user, tenant } = requireAdmin(event)
  const person = pendingOf(tenant, getRouterParam(event, 'id'))
  const { reason } = parseBody(rejectBody, body ?? {})
  removePerson(tenant, person)
  sendEmail(tenant, { to: person.email, key: 'notification', vars: { title: `Your request to join ${tenant.name}`, message: reason ? `It was not approved: ${reason}` : 'It was not approved. Ask the person who sent you the link if you think this is a mistake.', link: '', workspace: tenant.name }, reason: 'approval' })
  audit(event, tenant, user, 'users.rejected', person, reason ? { reason } : {})
  return ok({ id: person.id })
})

// ── The sign-up page (public) ────────────────────────────────────────────────────────

type Found = { tenant: MockTenant; kind: 'invite' | 'activation'; person: StoredPerson } | { tenant: MockTenant; kind: 'link'; person: null }
function findLink(event: H3Event, token: string): Found {
  const here = tenantOf(event).tenant
  const tenants = here ? [here] : MOCK_TENANTS
  const shared = tenantBySignupToken(tenants, token)
  if (shared) return { tenant: shared, kind: 'link', person: null }
  const wanted = hash(token)
  for (const tenant of tenants) {
    const person = peopleStoreOf(tenant).find(item => item.invite?.token_hash === wanted)
    if (person) {
      if (person.status !== 'invited' && person.status !== 'not_activated') break
      if (Date.parse(person.invite!.expires_at) < Date.now()) throw new MockError('FRM-USER-1001')
      return { tenant, kind: person.invite!.kind ?? 'invite', person }
    }
  }
  throw new MockError('FRM-USER-1002')
}

export const previewInvite = defineMockRoute(({ event }) => {
  const found = findLink(event, getRouterParam(event, 'token') ?? '')
  const { tenant, person } = found
  return ok<InvitePreview>({
    kind: found.kind,
    workspace: tenant.name,
    email: person?.email ?? null,
    first_name: person?.first_name ?? '',
    last_name: person?.last_name ?? '',
    inviter: person?.invite?.invited_by.name ?? null,
    role: person?.role ?? null,
    role_name: person ? (roleOf(tenant, person.role)?.name ?? person.role) : null,
    message: person?.invite?.message ?? null,
    domains: found.kind === 'link' ? signupLinkOf(tenant).domains : [],
  })
})

const acceptBody = z.object({ first_name: z.string().trim().min(1).max(60), last_name: z.string().trim().min(1).max(60), email: z.email().max(200).optional(), phone: z.string().trim().regex(/^\+[1-9][\d\s-]{6,18}$/).nullable().optional(), password: z.string().min(1).max(200) })

export const acceptInvite = defineMockRoute(({ event, body }) => {
  const found = findLink(event, getRouterParam(event, 'token') ?? '')
  const { tenant } = found
  const input = parseBody(acceptBody, body)
  checkNewPassword(tenant, null, input.password)
  const people = peopleStoreOf(tenant)
  let person = found.person
  if (!person) {
    // The shared link: a new person, with the email they typed (checked against the domains)
    const email = (input.email ?? '').trim().toLowerCase()
    if (!email) throw new MockError('FRM-GEN-1002', [{ field: 'email', message: 'required' }])
    if (people.some(item => item.email.toLowerCase() === email) || MOCK_USERS.some(item => item.tenant_id === tenant.id && item.email.toLowerCase() === email)) throw new MockError('FRM-USER-1011')
    const domains = signupLinkOf(tenant).domains
    if (domains.length && !domains.includes(email.split('@')[1] ?? '')) throw new MockError('FRM-USER-1012', [{ field: 'email', message: domains.join(', ') }])
    person = { id: crypto.randomUUID(), first_name: '', last_name: '', email, phone: null, role: 'member', status: 'pending', manager_id: null, two_step: false, joined_at: new Date().toISOString() }
    people.push(person)
  }
  const activation = found.kind === 'activation'
  const phone = input.phone?.replace(/[\s-]/g, '') ?? person.phone ?? null
  const account: MockUser = { id: person.id, tenant_id: tenant.id, first_name: input.first_name, last_name: input.last_name, email: person.email, password: hashPassword(input.password), phone, disabled: false, role: person.role, password_changed_at: new Date().toISOString(), awaiting_approval: !activation }
  MOCK_USERS.push(account)
  saveCreatedWorkspaces()
  Object.assign(person, { first_name: input.first_name, last_name: input.last_name, phone, password_hash: account.password, status: activation ? 'active' : 'pending', ...(activation ? { joined_at: new Date().toISOString() } : { request: { via: found.kind === 'link' ? 'link' : 'invite', at: new Date().toISOString() } }) })
  delete person.invite
  savePeople()
  recordAudit(event, tenant, { action: activation ? 'users.joined' : 'users.requested', actor: actorOf(account), resource: { type: 'user', id: person.id, name: nameOf(account) }, metadata: { via: found.kind } })
  return ok({ email: person.email, status: person.status })
})

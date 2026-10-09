/**
 * Invitations (F16 M2, docs/API-CONTRACT.md → People). An admin invites people by email with their role,
 * departments and job titles set at once; each gets the workspace's invitation email with a link that
 * works for 7 days. Only a hash of the link's token is kept, so a new link (resend, copy link) replaces
 * the old one. The person opens the link, sets their name and password, and is in the workspace.
 *
 *   POST   /people/invites                 InviteRequest → InviteResult
 *   POST   /people/:id/invite/resend       a new link by email
 *   POST   /people/:id/invite/link         a new link to copy (no email)
 *   DELETE /people/:id/invite              withdraw (the person and their memberships go)
 *   GET    /public/invites/:token          InvitePreview (the invitation page)
 *   POST   /public/invites/:token/accept   { first_name, last_name, password } → { email }
 */
import { createHash, randomBytes } from 'node:crypto'
import type { H3Event } from 'h3'
import { z } from 'zod'
import type { InvitePreview, InviteResult } from '#shared/types/people'
import { actorOf, recordAudit } from '../core/audit'
import { requireAdmin, tenantOf } from '../core/auth'
import { MockError, ok } from '../core/respond'
import { defineMockRoute } from '../core/route'
import { parseBody } from '../core/validate'
import { sendEmail } from '../data/outboxStore'
import { orgOf, saveOrg } from '../data/orgStore'
import { peopleStoreOf, savePeople, type StoredPerson } from '../data/peopleStore'
import { MOCK_TENANTS, MOCK_USERS, saveCreatedWorkspaces, type MockTenant, type MockUser } from '../data/tenants'
import { checkNewPassword } from './auth'
import { roleOf } from '../data/rolesStore'

const DAYS = 7
const hash = (token: string) => createHash('sha256').update(token).digest('hex')
const nameOf = (user: MockUser) => `${user.first_name} ${user.last_name}`.trim()

/** A new link for an invited person (the old one stops working). */
function freshLink(event: H3Event, tenant: MockTenant, person: StoredPerson, by: MockUser, message: string | null): string {
  const token = randomBytes(24).toString('base64url')
  const now = new Date()
  person.invite = { token_hash: hash(token), sent_at: now.toISOString(), expires_at: new Date(now.getTime() + DAYS * 86_400_000).toISOString(), invited_by: { id: by.id, name: nameOf(by) }, message }
  // The workspace's own address; on a dev host without one (localhost) the tenant rides along
  const url = getRequestURL(event, { xForwardedHost: true })
  const local = !url.hostname.includes(tenant.subdomain ?? '\u0000')
  return `${url.origin}/auth/join/${token}${local ? `?tenant=${tenant.subdomain}` : ''}`
}
function mail(tenant: MockTenant, person: StoredPerson, by: MockUser, link: string) {
  sendEmail(tenant, { to: person.email, key: 'invitation', vars: { name: person.first_name || person.email, inviter: nameOf(by), workspace: tenant.name, link }, reason: 'invitation' })
}
const invitedOf = (tenant: MockTenant, id: string | undefined) => {
  const person = peopleStoreOf(tenant).find(item => item.id === id)
  if (!person || person.status !== 'invited') throw new MockError('FRM-GEN-1004')
  return person
}
const audit = (event: H3Event, tenant: MockTenant, user: MockUser, action: 'users.invited' | 'users.invite_resent' | 'users.invite_link' | 'users.invite_revoked', person: StoredPerson, metadata: Record<string, string> = {}) =>
  recordAudit(event, tenant, { action, actor: actorOf(user), resource: { type: 'user', id: person.id, name: person.email }, metadata })

const inviteBody = z.object({
  emails: z.array(z.email().max(200)).min(1).max(50),
  // Any role but Owner (owners are made on People by owners)
  role: z.string().min(1).max(64).refine(value => value !== 'owner'),
  department_ids: z.array(z.string().max(64)).max(20).default([]),
  job_title_ids: z.array(z.string().max(64)).max(20).default([]),
  message: z.string().trim().max(500).nullable().optional(),
})

export const invitePeople = defineMockRoute(({ event, body }) => {
  const { user, tenant } = requireAdmin(event)
  const input = parseBody(inviteBody, body)
  if (!roleOf(tenant, input.role)) throw new MockError('FRM-USER-1009')
  const people = peopleStoreOf(tenant)
  const org = orgOf(tenant)
  const result: InviteResult = { invited: 0, skipped: [] }
  for (const email of [...new Set(input.emails.map(item => item.trim().toLowerCase()))]) {
    const existing = people.find(item => item.email.toLowerCase() === email)
    if (existing) {
      result.skipped.push({ email, reason: existing.status === 'invited' ? 'invited' : 'member' })
      continue
    }
    const person: StoredPerson = { id: crypto.randomUUID(), first_name: '', last_name: '', email, phone: null, role: input.role, status: 'invited', manager_id: null, two_step: false, joined_at: new Date().toISOString() }
    people.push(person)
    // Departments and job titles live in the organisation data, so Settings shows them too
    for (const item of org.departments) if (input.department_ids.includes(item.id) && !item.archived_at) item.member_ids.push(person.id)
    for (const item of org.job_titles) if (input.job_title_ids.includes(item.id) && !item.archived_at) item.member_ids.push(person.id)
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
  const person = invitedOf(tenant, getRouterParam(event, 'id'))
  mail(tenant, person, user, freshLink(event, tenant, person, user, person.invite?.message ?? null))
  savePeople()
  audit(event, tenant, user, 'users.invite_resent', person)
  return ok({ expires_at: person.invite!.expires_at })
})

export const inviteLink = defineMockRoute(({ event }) => {
  const { user, tenant } = requireAdmin(event)
  const person = invitedOf(tenant, getRouterParam(event, 'id'))
  const link = freshLink(event, tenant, person, user, person.invite?.message ?? null)
  savePeople()
  audit(event, tenant, user, 'users.invite_link', person)
  return ok({ link, expires_at: person.invite!.expires_at })
})

export const revokeInvite = defineMockRoute(({ event }) => {
  const { user, tenant } = requireAdmin(event)
  const person = invitedOf(tenant, getRouterParam(event, 'id'))
  const people = peopleStoreOf(tenant)
  people.splice(people.indexOf(person), 1)
  const org = orgOf(tenant)
  for (const item of [...org.departments, ...org.job_titles]) item.member_ids = item.member_ids.filter(id => id !== person.id)
  savePeople()
  saveOrg()
  audit(event, tenant, user, 'users.invite_revoked', person)
  return ok({ id: person.id })
})

/** The invitation behind a link, wherever it is opened (the token names the workspace). */
function findInvite(event: H3Event, token: string): { tenant: MockTenant; person: StoredPerson } {
  const wanted = hash(token)
  const here = tenantOf(event).tenant
  for (const tenant of here ? [here] : MOCK_TENANTS) {
    const person = peopleStoreOf(tenant).find(item => item.invite?.token_hash === wanted)
    if (person) {
      if (person.status !== 'invited') break
      if (Date.parse(person.invite!.expires_at) < Date.now()) throw new MockError('FRM-USER-1001')
      return { tenant, person }
    }
  }
  throw new MockError('FRM-USER-1002')
}

export const previewInvite = defineMockRoute(({ event }) => {
  const { tenant, person } = findInvite(event, getRouterParam(event, 'token') ?? '')
  return ok<InvitePreview>({ workspace: tenant.name, email: person.email, inviter: person.invite!.invited_by.name, role: person.role, role_name: roleOf(tenant, person.role)?.name ?? person.role, message: person.invite!.message })
})

const acceptBody = z.object({ first_name: z.string().trim().min(1).max(60), last_name: z.string().trim().min(1).max(60), password: z.string().min(1).max(200) })

export const acceptInvite = defineMockRoute(({ event, body }) => {
  const { tenant, person } = findInvite(event, getRouterParam(event, 'token') ?? '')
  const input = parseBody(acceptBody, body)
  checkNewPassword(tenant, null, input.password)
  const user: MockUser = { id: person.id, tenant_id: tenant.id, first_name: input.first_name, last_name: input.last_name, email: person.email, password: input.password, phone: null, disabled: false, role: person.role, password_changed_at: new Date().toISOString() }
  MOCK_USERS.push(user)
  saveCreatedWorkspaces()
  Object.assign(person, { first_name: input.first_name, last_name: input.last_name, status: 'active', joined_at: new Date().toISOString() })
  const invitedBy = person.invite!.invited_by.name
  delete person.invite
  savePeople()
  recordAudit(event, tenant, { action: 'users.joined', actor: actorOf(user), resource: { type: 'user', id: user.id, name: nameOf(user) }, metadata: { invited_by: invitedBy } })
  return ok({ email: user.email })
})

/**
 * Managing people (F16 M3, docs/API-CONTRACT.md → People). Admins and owners change a person's role,
 * departments, job titles and manager, disable or enable them, sign them out everywhere, ask for a new
 * password at the next sign-in, and reset two-step sign-in; several at once through `bulk`.
 * Guards: a workspace keeps at least one active owner; only owners make or change owners; nobody
 * disables or demotes themselves here; a manager can't be the person or someone who reports to them.
 *
 *   PATCH /people/:id                 { role?, department_ids?, job_title_ids?, manager_id? }
 *   POST  /people/:id/disable · /enable · /sign-out · /password · /two-step/reset
 *   POST  /people/bulk                { ids, action: role|department|job_title|disable|enable, value? } → { done, skipped }
 */
import type { H3Event } from 'h3'
import { z } from 'zod'
import type { AuditChange } from '#shared/types/audit'
import type { WorkspaceRole } from '#shared/types/auth'
import type { AuditAction } from '#shared/utils/audit/events'
import { actorOf, recordAudit } from '../core/audit'
import { requireAdmin, revokeUserSessions } from '../core/auth'
import { MockError, ok } from '../core/respond'
import { defineMockRoute } from '../core/route'
import { parseBody } from '../core/validate'
import { orgOf, saveOrg } from '../data/orgStore'
import { accountOf, peopleStoreOf, personDetail, savePeople, type StoredPerson } from '../data/peopleStore'
import type { MockTenant, MockUser } from '../data/tenants'
import { roleOf } from '../data/rolesStore'

const nameOf = (person: StoredPerson) => `${person.first_name} ${person.last_name}`.trim() || person.email
const activeOwners = (tenant: MockTenant) => peopleStoreOf(tenant).filter(item => item.role === 'owner' && item.status === 'active')

/** A person to act on; invitations can be edited (role, departments …) but not disabled or signed out. */
function find(tenant: MockTenant, id: string | undefined, invited = false): StoredPerson {
  const person = peopleStoreOf(tenant).find(item => item.id === id)
  if (!person || (person.status === 'invited' && !invited)) throw new MockError('FRM-GEN-1004')
  return person
}
const audit = (event: H3Event, tenant: MockTenant, user: MockUser, action: AuditAction, person: StoredPerson, changes: AuditChange[] = []) =>
  recordAudit(event, tenant, { action, actor: actorOf(user), resource: { type: 'user', id: person.id, name: nameOf(person) }, changes })

/** Owners are changed only by owners, and the last active owner stays one. */
function guardOwner(tenant: MockTenant, user: MockUser, person: StoredPerson, losing: boolean) {
  if (person.role === 'owner' && user.role !== 'owner') throw new MockError('FRM-USER-1006')
  if (losing && person.role === 'owner' && person.status === 'active' && activeOwners(tenant).length <= 1) throw new MockError('FRM-USER-1003')
}

function setRole(tenant: MockTenant, user: MockUser, person: StoredPerson, role: WorkspaceRole): AuditChange | null {
  if (role === person.role) return null
  if (!roleOf(tenant, role)) throw new MockError('FRM-USER-1009')
  if (role === 'owner' && user.role !== 'owner') throw new MockError('FRM-USER-1006')
  if (person.id === user.id && role !== 'owner' && person.role === 'owner' && activeOwners(tenant).length <= 1) throw new MockError('FRM-USER-1003')
  guardOwner(tenant, user, person, true)
  const before = person.role
  person.role = role
  const account = accountOf(person.id)
  if (account) account.role = role
  return { field: 'role', before, after: role }
}

/** Puts the person in exactly these entries of a kind (departments or job titles); the changed names. */
function setMemberships(tenant: MockTenant, kind: 'departments' | 'job_titles', person: StoredPerson, ids: string[]): AuditChange | null {
  const items = orgOf(tenant)[kind]
  const before = items.filter(item => item.member_ids.includes(person.id)).map(item => item.name)
  for (const item of items) {
    const wanted = ids.includes(item.id) && !item.archived_at
    const has = item.member_ids.includes(person.id)
    if (wanted && !has) item.member_ids.push(person.id)
    if (!wanted && has && !item.archived_at) item.member_ids = item.member_ids.filter(id => id !== person.id)
  }
  const after = items.filter(item => item.member_ids.includes(person.id)).map(item => item.name)
  return before.join(', ') === after.join(', ') ? null : { field: kind, before: before.join(', ') || null, after: after.join(', ') || null }
}

function setManager(tenant: MockTenant, person: StoredPerson, managerId: string | null): AuditChange | null {
  if (managerId === person.manager_id) return null
  const people = peopleStoreOf(tenant)
  if (managerId) {
    const manager = people.find(item => item.id === managerId && item.status !== 'invited')
    if (!manager) throw new MockError('FRM-GEN-1004')
    // Walk up from the new manager: reaching the person would make a loop
    for (let at: StoredPerson | undefined = manager, i = 0; at && i < 50; at = people.find(item => item.id === at!.manager_id), i++)
      if (at.id === person.id) throw new MockError('FRM-USER-1004')
  }
  const name = (id: string | null) => (id ? (people.find(item => item.id === id) ? nameOf(people.find(item => item.id === id)!) : null) : null)
  const change = { field: 'manager', before: name(person.manager_id), after: name(managerId) }
  person.manager_id = managerId
  return change
}

const patchBody = z.object({
  role: z.string().min(1).max(64).optional(),
  department_ids: z.array(z.string().max(64)).max(20).optional(),
  job_title_ids: z.array(z.string().max(64)).max(20).optional(),
  manager_id: z.string().max(64).nullable().optional(),
})

export const updatePerson = defineMockRoute(({ event, body }) => {
  const { user, tenant } = requireAdmin(event)
  const person = find(tenant, getRouterParam(event, 'id'), true)
  const input = parseBody(patchBody, body)
  const role = input.role ? setRole(tenant, user, person, input.role) : null
  const changes = [
    input.department_ids ? setMemberships(tenant, 'departments', person, input.department_ids) : null,
    input.job_title_ids ? setMemberships(tenant, 'job_titles', person, input.job_title_ids) : null,
    input.manager_id !== undefined ? setManager(tenant, person, input.manager_id) : null,
  ].filter((item): item is AuditChange => !!item)
  savePeople()
  saveOrg()
  if (role) audit(event, tenant, user, 'users.role_changed', person, [role])
  if (changes.length) audit(event, tenant, user, 'users.updated', person, changes)
  return ok(personDetail(tenant, person.id))
})

function disable(tenant: MockTenant, user: MockUser, person: StoredPerson): boolean {
  if (person.id === user.id) throw new MockError('FRM-USER-1005')
  if (person.status === 'disabled') return false
  guardOwner(tenant, user, person, true)
  person.status = 'disabled'
  const account = accountOf(person.id)
  if (account) account.disabled = true
  revokeUserSessions(tenant, person.id)
  return true
}
function enable(tenant: MockTenant, user: MockUser, person: StoredPerson): boolean {
  if (person.status !== 'disabled') return false
  guardOwner(tenant, user, person, false)
  person.status = 'active'
  const account = accountOf(person.id)
  if (account) account.disabled = false
  return true
}

/** One action on one person, then saved and audited. */
const action = (work: (tenant: MockTenant, user: MockUser, person: StoredPerson) => boolean, name: AuditAction) =>
  defineMockRoute(({ event }) => {
    const { user, tenant } = requireAdmin(event)
    const person = find(tenant, getRouterParam(event, 'id'))
    if (work(tenant, user, person)) {
      savePeople()
      audit(event, tenant, user, name, person)
    }
    return ok(personDetail(tenant, person.id))
  })

export const disablePerson = action(disable, 'users.disabled')
export const enablePerson = action(enable, 'users.enabled')
export const signOutPerson = action((tenant, user, person) => {
  guardOwner(tenant, user, person, false)
  revokeUserSessions(tenant, person.id)
  return true
}, 'users.signed_out')
export const requestPassword = action((tenant, user, person) => {
  if (person.id === user.id) throw new MockError('FRM-USER-1005')
  guardOwner(tenant, user, person, false)
  person.must_change_password = true
  const account = accountOf(person.id)
  if (account) account.must_change_password = true
  revokeUserSessions(tenant, person.id)
  return true
}, 'users.password_requested')
export const resetTwoStep = action((tenant, user, person) => {
  guardOwner(tenant, user, person, false)
  if (!person.two_step) return false
  person.two_step = false
  return true
}, 'users.two_step_reset')

const bulkBody = z.object({ ids: z.array(z.string().max(64)).min(1).max(200), action: z.enum(['role', 'department', 'job_title', 'disable', 'enable']), value: z.string().max(64).optional() })

export const bulkPeople = defineMockRoute(({ event, body }) => {
  const { user, tenant } = requireAdmin(event)
  const input = parseBody(bulkBody, body)
  let done = 0
  let skipped = 0
  for (const id of input.ids) {
    try {
      const person = find(tenant, id)
      let changed: AuditChange | boolean | null = null
      let name: AuditAction = 'users.updated'
      if (input.action === 'role') {
        changed = setRole(tenant, user, person, z.string().min(1).max(64).parse(input.value))
        name = 'users.role_changed'
      }
      // Adds to a department or job title (keeps the others)
      else if (input.action === 'department' || input.action === 'job_title') {
        const kind = input.action === 'department' ? 'departments' : 'job_titles'
        const current = orgOf(tenant)[kind].filter(item => item.member_ids.includes(person.id)).map(item => item.id)
        changed = setMemberships(tenant, kind, person, [...current, input.value ?? ''])
      } else if (input.action === 'disable') {
        changed = disable(tenant, user, person)
        name = 'users.disabled'
      } else {
        changed = enable(tenant, user, person)
        name = 'users.enabled'
      }
      if (changed) {
        audit(event, tenant, user, name, person, typeof changed === 'object' ? [changed] : [])
        done++
      } else skipped++
    } catch {
      skipped++
    }
  }
  savePeople()
  saveOrg()
  return ok({ done, skipped })
})

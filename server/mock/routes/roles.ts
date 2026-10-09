/**
 * Roles & access (F22, brought forward into F16; docs/API-CONTRACT.md → Roles). Reading needs
 * people.view, changing roles.manage (the permission table in shared/utils/auth/permissions.ts).
 *
 *   GET    /roles · /roles/insights · /roles/:id
 *   POST   /roles                 { name, description?, permissions } (or `copy_of` a role)
 *   PATCH  /roles/:id             { name?, description?, permissions? } (Owner can't be changed)
 *   POST   /roles/:id/duplicate
 *   DELETE /roles/:id             only the workspace's own roles nobody holds
 */
import type { H3Event } from 'h3'
import { z } from 'zod'
import type { RoleRow, RolesInsights } from '#shared/types/people'
import { ALL_PERMISSIONS, OWNER_ROLE, withNeeds } from '#shared/utils/auth/permissions'
import { actorOf, recordAudit } from '../core/audit'
import { requireAdmin } from '../core/auth'
import { MockError, ok, paginate } from '../core/respond'
import { defineMockRoute } from '../core/route'
import { parseBody } from '../core/validate'
import { peopleStoreOf } from '../data/peopleStore'
import { rolesOf, saveRoles, type StoredRole } from '../data/rolesStore'
import type { MockTenant, MockUser } from '../data/tenants'

function rowOf(tenant: MockTenant, role: StoredRole): RoleRow {
  const holders = peopleStoreOf(tenant).filter(person => person.role === role.id && person.status !== 'disabled')
  return {
    ...role,
    people_count: holders.length,
    people: holders.slice(0, 5).map(person => ({ id: person.id, name: `${person.first_name} ${person.last_name}`.trim() || person.email, photo: person.photo ?? null })),
  }
}
const find = (tenant: MockTenant, id: string | undefined) => {
  const role = rolesOf(tenant).find(item => item.id === id)
  if (!role) throw new MockError('FRM-GEN-1004')
  return role
}
const audit = (event: H3Event, tenant: MockTenant, user: MockUser, action: 'users.role_created' | 'users.role_updated' | 'users.role_deleted', role: StoredRole, changes: { field: string; before: string | null; after: string | null }[] = []) =>
  recordAudit(event, tenant, { action, actor: actorOf(user), resource: { type: 'role', id: role.id, name: role.name }, changes })
const assertName = (tenant: MockTenant, name: string, except?: string) => {
  if (rolesOf(tenant).some(role => role.id !== except && role.name.toLowerCase() === name.toLowerCase())) throw new MockError('FRM-ORG-1001', [{ field: 'name', message: 'taken' }])
}
const permissions = z.array(z.enum(ALL_PERMISSIONS as [string, ...string[]])).max(ALL_PERMISSIONS.length)

export const listRoles = defineMockRoute(({ event, query }) => {
  const { tenant } = requireAdmin(event)
  let rows = rolesOf(tenant).map(role => rowOf(tenant, role))
  if (query.page === undefined) return ok(rows)
  // filter[kind] = builtin · own
  const kind = typeof query['filter[kind]'] === 'string' ? query['filter[kind]'].split(',') : []
  if (kind.length) rows = rows.filter(row => kind.includes(row.built_in ? 'builtin' : 'own'))
  const sort = typeof query.sort === 'string' ? query.sort : 'name'
  const key = sort.replace(/^-/, '') as 'name' | 'people_count' | 'updated_at'
  rows.sort((a, b) => (sort.startsWith('-') ? -1 : 1) * (key === 'people_count' ? a.people_count - b.people_count : String(a[key]).localeCompare(String(b[key]))))
  const { data, meta } = paginate(rows, { ...query, sort: undefined }, (row, q) => `${row.name} ${row.description ?? ''}`.toLowerCase().includes(q))
  return ok(data, meta)
})

export const rolesInsights = defineMockRoute(({ event }) => {
  const { tenant } = requireAdmin(event)
  const rows = rolesOf(tenant).map(role => rowOf(tenant, role))
  return ok<RolesInsights>({
    total: rows.length,
    custom: rows.filter(row => !row.built_in).length,
    people: rows.reduce((sum, row) => sum + row.people_count, 0),
    by_role: [...rows].sort((a, b) => b.people_count - a.people_count).map(row => ({ id: row.id, name: row.name, count: row.people_count })),
    reach: rows.map(row => ({ id: row.id, name: row.name, share: withNeeds(row.permissions).length / ALL_PERMISSIONS.length })),
  })
})

export const getRole = defineMockRoute(({ event }) => {
  const { tenant } = requireAdmin(event)
  return ok(rowOf(tenant, find(tenant, getRouterParam(event, 'id'))))
})

const createBody = z.object({ name: z.string().trim().min(1).max(60), description: z.string().trim().max(300).nullable().optional(), permissions: permissions.optional(), copy_of: z.string().max(64).optional() })

export const createRole = defineMockRoute(({ event, body }) => {
  const { user, tenant } = requireAdmin(event)
  const input = parseBody(createBody, body)
  assertName(tenant, input.name)
  const source = input.copy_of ? find(tenant, input.copy_of) : null
  const now = new Date().toISOString()
  const role: StoredRole = { id: `role_${crypto.randomUUID().slice(0, 8)}`, name: input.name, description: input.description ?? source?.description ?? null, permissions: withNeeds(input.permissions ?? source?.permissions ?? []), built_in: null, created_at: now, updated_at: now }
  rolesOf(tenant).push(role)
  saveRoles()
  audit(event, tenant, user, 'users.role_created', role)
  return ok(rowOf(tenant, role), {}, 201)
})

const patchBody = z.object({ name: z.string().trim().min(1).max(60).optional(), description: z.string().trim().max(300).nullable().optional(), permissions: permissions.optional() })

export const updateRole = defineMockRoute(({ event, body }) => {
  const { user, tenant } = requireAdmin(event)
  const role = find(tenant, getRouterParam(event, 'id'))
  if (role.id === OWNER_ROLE) throw new MockError('FRM-USER-1007')
  const input = parseBody(patchBody, body)
  if (input.name) assertName(tenant, input.name, role.id)
  const next = input.permissions ? withNeeds(input.permissions) : role.permissions
  const added = next.filter(item => !role.permissions.includes(item))
  const removed = role.permissions.filter(item => !next.includes(item))
  const changes = [
    ...(input.name && input.name !== role.name ? [{ field: 'name', before: role.name, after: input.name }] : []),
    ...(input.description !== undefined && (input.description ?? null) !== role.description ? [{ field: 'description', before: role.description, after: input.description ?? null }] : []),
    ...(added.length ? [{ field: 'permissions_added', before: null, after: added.join(', ') }] : []),
    ...(removed.length ? [{ field: 'permissions_removed', before: removed.join(', '), after: null }] : []),
  ]
  Object.assign(role, { ...(input.name ? { name: input.name } : {}), ...(input.description !== undefined ? { description: input.description ?? null } : {}), permissions: next, updated_at: new Date().toISOString() })
  saveRoles()
  if (changes.length) audit(event, tenant, user, 'users.role_updated', role, changes)
  return ok(rowOf(tenant, role))
})

export const duplicateRole = defineMockRoute(({ event }) => {
  const { user, tenant } = requireAdmin(event)
  const source = find(tenant, getRouterParam(event, 'id'))
  let name = `${source.name} (copy)`.slice(0, 60)
  for (let n = 2; rolesOf(tenant).some(role => role.name.toLowerCase() === name.toLowerCase()); n++) name = `${source.name} (copy ${n})`.slice(0, 60)
  const now = new Date().toISOString()
  const role: StoredRole = { id: `role_${crypto.randomUUID().slice(0, 8)}`, name, description: source.description, permissions: [...source.permissions], built_in: null, created_at: now, updated_at: now }
  rolesOf(tenant).push(role)
  saveRoles()
  audit(event, tenant, user, 'users.role_created', role)
  return ok(rowOf(tenant, role), {}, 201)
})

export const deleteRole = defineMockRoute(({ event }) => {
  const { user, tenant } = requireAdmin(event)
  const role = find(tenant, getRouterParam(event, 'id'))
  if (role.built_in) throw new MockError('FRM-USER-1007')
  if (peopleStoreOf(tenant).some(person => person.role === role.id)) throw new MockError('FRM-USER-1008')
  const list = rolesOf(tenant)
  list.splice(list.indexOf(role), 1)
  saveRoles()
  audit(event, tenant, user, 'users.role_deleted', role)
  return ok({ id: role.id })
})

/**
 * Roles of each workspace in the mock (F22, brought forward into F16; `.data/mock/roles.json`). Every
 * workspace starts with Owner (everything, can't be changed or deleted), Admin and Member (editable
 * defaults); owners add their own. A person's `role` is a role id. A role holds grants: each action with
 * its scope (own · shared · all, F22 R2).
 */
import type { Grants, Permission, Scope } from '#shared/utils/auth/permissions'
import { ALL_GRANTS, ALL_PERMISSIONS, BUILT_IN_ROLES, DEFAULT_ROLE_GRANTS, OWNER_ROLE, grantsFromList, withNeeds } from '#shared/utils/auth/permissions'
import { loadPersisted, savePersisted } from '../core/persist'
import { MOCK_TENANTS, type MockTenant, type MockUser } from './tenants'

export interface StoredRole {
  id: string
  name: string
  description: string | null
  grants: Grants
  /** owner · admin · member for the built-in ones; null for the workspace's own. */
  built_in: (typeof BUILT_IN_ROLES)[number] | null
  /** 2 = response actions have scopes (F22 R2 M2); 3 = "shared" split into shared and own & shared. */
  version?: number
  created_at: string
  updated_at: string
}

const stores = new Map<string, StoredRole[]>(Object.entries(loadPersisted<Record<string, StoredRole[]>>('roles', {})))
export const saveRoles = () => savePersisted('roles', () => Object.fromEntries(stores))

// Roles saved before scopes kept a list of permissions: the same reach as grants (2026-10-10).
// Review responses was split from Edit (2026-10-09): roles that could edit keep reviewing.
let migrated = false
for (const role of [...stores.values()].flat() as (StoredRole & { permissions?: string[] })[])
  if (role.permissions && !role.grants) {
    const list = role.permissions.includes('responses.edit') ? [...role.permissions, 'responses.review'] : role.permissions
    role.grants = grantsFromList(list)
    delete role.permissions
    migrated = true
  }
// Responses got scopes (F22 R2 M2): before, a person saw responses of the forms they could see, so a
// role that didn't see every form reaches "shared" responses; one that did keeps "all".
for (const role of [...stores.values()].flat())
  if ((role.version ?? 1) < 2) {
    const reach = role.grants['forms.view'] === 'all' ? 'all' : 'own_shared'
    for (const key of Object.keys(role.grants) as (keyof Grants)[]) if (key.startsWith('responses.')) role.grants[key] = reach
    role.version = 2
    migrated = true
  }
// "Shared" meant own and shared until 2026-10-10 (owner: None, Own, Shared, Own & Shared, All): it becomes own_shared
for (const role of [...stores.values()].flat())
  if ((role.version ?? 1) < 3) {
    for (const key of Object.keys(role.grants) as (keyof Grants)[]) if (role.grants[key] === 'shared') role.grants[key] = 'own_shared'
    role.version = 3
    migrated = true
  }
if (migrated) saveRoles()

const NAMES = { owner: 'Owner', admin: 'Admin', member: 'Member' } as const
const DESCRIPTIONS = {
  owner: "Everything, including roles and the workspace itself. It can't be changed.",
  admin: 'Manages people, forms, data, the API service and settings.',
  member: 'Builds and publishes forms and works with their responses.',
} as const

export function rolesOf(tenant: MockTenant): StoredRole[] {
  let list = stores.get(tenant.id)
  if (!list) {
    const at = new Date().toISOString()
    list = BUILT_IN_ROLES.map(id => ({ id, name: NAMES[id], description: DESCRIPTIONS[id], grants: { ...DEFAULT_ROLE_GRANTS[id] }, built_in: id, version: 3, created_at: at, updated_at: at }))
    stores.set(tenant.id, list)
    saveRoles()
  }
  // Owner always holds everything there is (new actions included)
  const owner = list.find(role => role.id === OWNER_ROLE)
  if (owner) Object.assign(owner, { grants: { ...ALL_GRANTS }, name: NAMES.owner, description: DESCRIPTIONS.owner })
  return list
}

export const roleOf = (tenant: MockTenant, id: string) => rolesOf(tenant).find(role => role.id === id) ?? null

/** What this account may do, with each action's scope (a role that is gone gives nothing). */
export function grantsOf(user: MockUser, tenant?: MockTenant): Grants {
  if (user.role === OWNER_ROLE) return ALL_GRANTS
  const where = tenant ?? MOCK_TENANTS.find(item => item.id === user.tenant_id)
  // No workspace to read roles from (tests, a workspace being made): the built-in defaults
  if (!where) return withNeeds(DEFAULT_ROLE_GRANTS[user.role as keyof typeof DEFAULT_ROLE_GRANTS] ?? {})
  return withNeeds(roleOf(where, user.role)?.grants ?? {})
}
/** The actions this account holds, whatever their scope. */
export const permissionsOf = (user: MockUser, tenant?: MockTenant): Set<Permission> => new Set(ALL_PERMISSIONS.filter(item => grantsOf(user, tenant)[item]))
export const can = (user: MockUser, permission: Permission, tenant?: MockTenant) => !!grantsOf(user, tenant)[permission]
/** How far an action reaches for this account: own · shared · all, or null when not at all. */
export const scopeOf = (user: MockUser, permission: Permission, tenant?: MockTenant): Scope | null => grantsOf(user, tenant)[permission] ?? null

/**
 * Roles of each workspace in the mock (F22, brought forward into F16; `.data/mock/roles.json`). Every
 * workspace starts with Owner (everything, can't be changed or deleted), Admin and Member (editable
 * defaults); owners add their own. A person's `role` is a role id.
 */
import type { Permission } from '#shared/utils/auth/permissions'
import { ALL_PERMISSIONS, BUILT_IN_ROLES, DEFAULT_ROLE_PERMISSIONS, OWNER_ROLE, withNeeds } from '#shared/utils/auth/permissions'
import { loadPersisted, savePersisted } from '../core/persist'
import { MOCK_TENANTS, type MockTenant, type MockUser } from './tenants'

export interface StoredRole {
  id: string
  name: string
  description: string | null
  permissions: Permission[]
  /** owner · admin · member for the built-in ones; null for the workspace's own. */
  built_in: (typeof BUILT_IN_ROLES)[number] | null
  created_at: string
  updated_at: string
}

const stores = new Map<string, StoredRole[]>(Object.entries(loadPersisted<Record<string, StoredRole[]>>('roles', {})))
export const saveRoles = () => savePersisted('roles', () => Object.fromEntries(stores))

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
    list = BUILT_IN_ROLES.map(id => ({ id, name: NAMES[id], description: DESCRIPTIONS[id], permissions: [...DEFAULT_ROLE_PERMISSIONS[id]], built_in: id, created_at: at, updated_at: at }))
    stores.set(tenant.id, list)
    saveRoles()
  }
  // Owner always holds everything there is (new permissions included)
  const owner = list.find(role => role.id === OWNER_ROLE)
  if (owner) Object.assign(owner, { permissions: [...ALL_PERMISSIONS], name: NAMES.owner, description: DESCRIPTIONS.owner })
  return list
}

export const roleOf = (tenant: MockTenant, id: string) => rolesOf(tenant).find(role => role.id === id) ?? null

/** What this account may do: its role's permissions (a role that is gone gives nothing). */
export function permissionsOf(user: MockUser, tenant?: MockTenant): Set<Permission> {
  if (user.role === OWNER_ROLE) return new Set(ALL_PERMISSIONS)
  const where = tenant ?? MOCK_TENANTS.find(item => item.id === user.tenant_id)
  // No workspace to read roles from (tests, a workspace being made): the built-in defaults
  if (!where) return new Set(withNeeds(DEFAULT_ROLE_PERMISSIONS[user.role as keyof typeof DEFAULT_ROLE_PERMISSIONS] ?? []))
  return new Set(withNeeds(roleOf(where, user.role)?.permissions ?? []))
}
export const can = (user: MockUser, permission: Permission, tenant?: MockTenant) => permissionsOf(user, tenant).has(permission)

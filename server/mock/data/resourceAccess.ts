/**
 * Who may change an item of a workspace library (F22 R2 M3, owner 2026-10-10): templates, lists,
 * themes, landing pages and saved fields. Formalie's own items (author `system`) are use-only for everyone
 * in a workspace (they're managed in the platform console, F23). Otherwise the role's grant for
 * `<area>.edit` / `<area>.delete` and its scope: own (they made it) · all.
 */
import { MockError } from '../core/respond'
import type { Permission } from '#shared/utils/auth/permissions'
import { scopeOf } from './rolesStore'
import type { MockTenant, MockUser } from './tenants'

export type ResourceArea = 'templates' | 'lists' | 'themes' | 'pages' | 'fields'
export interface ResourceActions {
  edit: boolean
  delete: boolean
}
interface Item {
  source?: string | null
  created_by?: { id: string } | null
}

/** Formalie's built-in item, never changed from a workspace. */
export const isSystemItem = (item: Item) => item.source === 'system' || item.created_by?.id === 'system'

function reach(area: ResourceArea, action: 'edit' | 'delete', item: Item, user: MockUser, tenant?: MockTenant): boolean {
  if (isSystemItem(item)) return false
  const scope = scopeOf(user, `${area}.${action}` as never, tenant)
  return scope === 'all' || (scope === 'own' && item.created_by?.id === user.id)
}

/** What this person may do with this item (sent with every row as `can`). */
export const resourceActions = (area: ResourceArea, item: Item, user: MockUser, tenant?: MockTenant): ResourceActions => ({
  edit: area !== 'fields' && reach(area, 'edit', item, user, tenant),
  delete: reach(area, 'delete', item, user, tenant),
})

/** Allowed, else refused (FRM-PERM-1001): built-in items and other people's items without "all". */
export function requireResource(area: ResourceArea, action: 'edit' | 'delete', item: Item, user: MockUser, tenant?: MockTenant) {
  if (!reach(area, action, item, user, tenant)) throw new MockError('FRM-PERM-1001')
}

/** own · all for any action on an item that records its maker (data connections, API services, F22 R2 M4). */
export function ownedReach(permission: Permission, item: Item, user: MockUser, tenant?: MockTenant): boolean {
  const scope = scopeOf(user, permission, tenant)
  return scope === 'all' || (scope === 'own' && item.created_by?.id === user.id)
}
export function requireOwned(permission: Permission, item: Item, user: MockUser, tenant?: MockTenant) {
  if (!ownedReach(permission, item, user, tenant)) throw new MockError('FRM-PERM-1001')
}

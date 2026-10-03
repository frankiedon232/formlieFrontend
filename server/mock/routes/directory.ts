/**
 * Mock directory (docs/API-CONTRACT.md → Directory): departments, roles and people of the workspace,
 * used to restrict a field to some of them (field access). Real departments arrive with Users (F17)
 * and custom roles with Roles & access (F22); the shape stays the same.
 */
import type { Directory } from '#shared/types/directory'
import { requireAuth } from '../core/auth'
import { ok } from '../core/respond'
import { defineMockRoute } from '../core/route'
import { MOCK_OWNERS } from '../data/forms'
import { MOCK_USERS } from '../data/tenants'

const DEPARTMENTS = ['Finance', 'Operations', 'People', 'Sales', 'Support', 'Technology', 'Legal', 'Compliance']
const ROLES = [
  { id: 'owner', name: 'Owner' },
  { id: 'admin', name: 'Administrator' },
  { id: 'member', name: 'Member' },
]

export const getDirectory = defineMockRoute(({ event }) => {
  const { tenant } = requireAuth(event)
  const domain = `${tenant.subdomain}.test`
  const directory: Directory = {
    departments: DEPARTMENTS.map(name => ({ id: `dep_${name.toLowerCase()}`, name })),
    roles: ROLES,
    users: [
      ...MOCK_USERS.filter(user => user.tenant_id === tenant.id && !user.disabled).map(user => ({
        id: user.id,
        name: `${user.first_name} ${user.last_name}`.trim(),
        detail: user.email,
      })),
      ...MOCK_OWNERS.map(owner => ({ id: owner.id, name: owner.name, detail: `${owner.name.toLowerCase().replace(/\s+/g, '.')}@${domain}` })),
    ],
  }
  return ok(directory)
})

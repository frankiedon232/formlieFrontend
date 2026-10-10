/**
 * The workspace directory (docs/API-CONTRACT.md → Directory): its departments and job titles (Settings →
 * Organisation data, F14 M2; archived ones flagged so forms still using them can name them), the
 * permission roles, and its people. Field access, people pickers and logic read it; any member.
 */
import type { Directory } from '#shared/types/directory'
import { requireAuth } from '../core/auth'
import { ok } from '../core/respond'
import { defineMockRoute } from '../core/route'
import { orgOf, peopleOf } from '../data/orgStore'
import { rolesOf } from '../data/rolesStore'


export const getDirectory = defineMockRoute(({ event }) => {
  const { tenant } = requireAuth(event)
  const org = orgOf(tenant)
  const list = (items: typeof org.departments) => items.map(item => ({ id: item.id, name: item.name, ...(item.code ? { detail: item.code } : {}), ...(item.archived_at ? { archived: true } : {}) }))
  const directory: Directory = {
    departments: list(org.departments),
    job_titles: list(org.job_titles),
    // The workspace's own roles (Roles & access), not a fixed list
    roles: rolesOf(tenant).map(role => ({ id: role.id, name: role.name })),
    users: peopleOf(tenant).map(person => ({ id: person.id, name: person.name, detail: person.email })),
  }
  return ok(directory)
})

/**
 * The workspace's roles (Roles & access, F22) for pickers and filters on People: loaded once and kept for
 * a minute; `refresh(true)` after roles change. People who can't see People get none.
 */
import type { RoleRow } from '#shared/types/people'

const roles = shallowRef<RoleRow[]>([])
let loadedAt = 0
let pending: Promise<void> | null = null

export function useRoles() {
  const api = useApi()
  const { can } = useCan()
  function refresh(force = false): Promise<void> {
    if (!can('people.view')) return Promise.resolve()
    if (pending) return pending
    if (!force && Date.now() - loadedAt < 60_000) return Promise.resolve()
    pending = (async () => {
      try {
        roles.value = (await api.get<RoleRow[]>('/roles', undefined, { background: true })).data
        loadedAt = Date.now()
      } catch {
        // Keep the last list
      } finally {
        pending = null
      }
    })()
    return pending
  }
  return { roles: readonly(roles), refresh }
}

import type { NavCounts } from '#shared/types/navigation'

// Module-level (client only, not secret): one copy shared by the sidebar, peek and rail.
const counts = shallowRef<NavCounts | null>(null)
let lastLoaded = 0
let pending: Promise<void> | null = null
const STALE_MS = 20_000

/**
 * Sidebar badge numbers. Loaded once signed in and refreshed on navigation when older than 20 s;
 * pages that change counts (create / archive a form…) call `refresh(true)`.
 */
export function useNavCounts() {
  const api = useApi()
  const session = useSession()

  function refresh(force = false): Promise<void> {
    if (!session.isAuthenticated.value) return Promise.resolve()
    if (pending) return pending
    if (!force && Date.now() - lastLoaded < STALE_MS) return Promise.resolve()
    pending = (async () => {
      try {
        counts.value = (await api.get<NavCounts>('/navigation/counts')).data
        lastLoaded = Date.now()
      } catch {
        // Badges are a nice-to-have: keep the last numbers (or none) and try again on the next navigation.
      } finally {
        pending = null
      }
    })()
    return pending
  }

  function clear() {
    counts.value = null
    lastLoaded = 0
  }

  return { counts: readonly(counts), refresh, clear }
}

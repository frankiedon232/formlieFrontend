/**
 * The team in the header (design: overlapping avatars "+10" and Add Member, F16 M4): the most recently
 * active people for owners and admins. Loaded once and kept for a minute, shared by every page header;
 * `refresh(true)` after People changes.
 */
import type { PersonRow } from '#shared/types/people'

const team = shallowRef<{ people: PersonRow[]; total: number } | null>(null)
let loadedAt = 0
let pending: Promise<void> | null = null

export function useTeam() {
  const api = useApi()
  const session = useSession()
  const { can } = useCan()
  const canSee = computed(() => !!session.user.value && can('people.view'))

  function refresh(force = false): Promise<void> {
    if (!canSee.value) return Promise.resolve()
    if (pending) return pending
    if (!force && Date.now() - loadedAt < 60_000) return Promise.resolve()
    pending = (async () => {
      try {
        const result = await api.list<PersonRow>('/people', { page_size: 8, sort: '-last_active_at', 'filter[status]': 'active' }, { background: true })
        team.value = { people: result.data, total: result.meta?.total ?? result.data.length }
        loadedAt = Date.now()
      } catch {
        // Avatars are a nice-to-have: keep the last ones
      } finally {
        pending = null
      }
    })()
    return pending
  }

  return { team: readonly(team), canSee, refresh }
}

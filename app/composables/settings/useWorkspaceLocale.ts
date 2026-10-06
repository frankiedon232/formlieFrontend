/**
 * The workspace's language and region (Settings → Language and region, F14): its time zone, date and
 * number formats, currency and the languages forms may use. Loaded once per signed-in session (any
 * member may read it) and kept in step when an admin saves. useFormat applies it everywhere.
 */
import type { LocalisationSettings } from '#shared/types/settings'

const state = ref<LocalisationSettings | null>(null)
/** The signed-in person it was loaded for: another sign-in loads the other workspace's. */
let loadedFor: string | null = null

/** Group and decimal signs for each number format. */
export const NUMBER_SIGNS: Record<LocalisationSettings['number_format'], { group: string; decimal: string }> = {
  '1,234.56': { group: ',', decimal: '.' },
  '1.234,56': { group: '.', decimal: ',' },
  '1 234,56': { group: ' ', decimal: ',' },
  "1'234.56": { group: "'", decimal: '.' },
}

export function useWorkspaceLocale() {
  const session = useSession()
  const user = session.user.value
  if (import.meta.client && user && loadedFor !== user.id) {
    loadedFor = user.id
    state.value = null
    useApi()
      .get<LocalisationSettings>('/settings/localisation', undefined, { background: true })
      .then(result => void (state.value = result.data))
      .catch(() => void (loadedFor = null))
  }
  /** Put a saved section in place (Settings → Language and region). */
  const set = (value: LocalisationSettings) => void (state.value = value)
  return { locale: readonly(state), set }
}

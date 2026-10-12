/**
 * Switches the Formalie team turns on per plan, per workspace or for a share of workspaces (B16,
 * `GET /platform/feature-flags`). Loaded once per sign-in; a missing key is off.
 *
 *   const flags = useFeatureFlags()
 *   <UButton v-if="flags.isOn('new_builder')" … />
 */
import type { FeatureFlags } from '#shared/types/support'

const flags = ref<FeatureFlags>({})
let loadedFor: string | null = null

export function useFeatureFlags() {
  const api = useApi()
  const session = useSession()

  async function load(force = false) {
    const user = session.user.value?.id ?? null
    if (!user || (!force && loadedFor === user)) return
    loadedFor = user
    try {
      flags.value = (await api.get<FeatureFlags>('/platform/feature-flags', undefined, { background: true })).data ?? {}
    } catch {
      loadedFor = null
    }
  }

  const isOn = (key: string) => flags.value[key] === true

  return { flags: readonly(flags), isOn, load }
}

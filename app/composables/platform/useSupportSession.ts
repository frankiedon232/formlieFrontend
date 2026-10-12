/**
 * Formalie support session banner (B16): while Formalie support is in the workspace, everyone sees who
 * and until when. One shared state for the whole app, checked every minute in the background
 * (`GET /support-access/status`), plus a one-second clock for the countdown.
 */
import type { SupportBanner } from '#shared/types/support'

const banner = ref<SupportBanner | null>(null)
let started = false

export function useSupportSession() {
  const api = useApi()
  const session = useSession()
  const now = ref(Date.now())
  useIntervalFn(() => (now.value = Date.now()), 1000)

  async function load() {
    if (!session.isAuthenticated.value) return
    try {
      banner.value = (await api.get<SupportBanner | null>('/support-access/status', undefined, { background: true })).data ?? null
    } catch {
      // Keep what we had; the next check tries again
    }
  }

  /** Starts the one-minute check (once for the whole app). */
  function start() {
    if (started || import.meta.server) return
    started = true
    void load()
    useIntervalFn(() => void load(), 60_000)
    // Signing in as someone else (or out) changes what applies
    watch(() => session.user.value?.id, () => void load())
  }

  const left = computed(() => msLeft(banner.value?.ends_at, now.value))
  const active = computed(() => !!banner.value && (left.value ?? 1) > 0)
  /** True only in the support person's own browser. */
  const isSupport = computed(() => !!session.user.value?.support)

  return { banner: readonly(banner), active, left, isSupport, load, start }
}

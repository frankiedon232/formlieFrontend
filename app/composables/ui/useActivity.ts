/**
 * One counter for "something is happening": in-app navigation and every API call (CLAUDE.md
 * rule 5). It drives both the top-of-window bar (<NuxtLoadingIndicator>) and the in-page sweeping
 * bar under each page header (<AppPanel>). Background polling doesn't count.
 *
 *   const done = useActivity().begin()   // … later
 *   done()
 */
const pending = ref(0)
let nuxtApp: ReturnType<typeof useNuxtApp> | null = null

// Looked up on every use: Nuxt recreates the shared indicator when its components remount.
const indicator = () =>
  nuxtApp?.runWithContext(() => useLoadingIndicator()) as ReturnType<typeof useLoadingIndicator> | undefined

export function useActivity() {
  nuxtApp ??= tryUseNuxtApp()

  /** Starts one unit of work; call the returned function exactly once when it ends. */
  function begin({ immediate = false } = {}): () => void {
    if (pending.value++ === 0) indicator()?.start({ force: immediate })
    let ended = false
    return () => {
      if (ended) return
      ended = true
      if (--pending.value === 0) indicator()?.finish()
    }
  }

  return { busy: computed(() => pending.value > 0), begin }
}

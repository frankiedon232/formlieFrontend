/**
 * Formalie's platform settings from GET {API}/public/platform (docs/API-HOOKS.md): support and sales addresses,
 * status page, social profiles and legal entity, as the owner sets them in the platform admin. Read while the
 * page is prerendered and again in the browser; the defaults (app/utils/platform.ts) cover an API that doesn't answer.
 */
export function usePlatform() {
  const links = useSiteLinks()

  const { data, refresh } = useAsyncData(
    'platform',
    async () => {
      try {
        const answer = await $fetch(links.api('public/platform'), { timeout: 5000, retry: 0 })
        return parsePlatform(answer) ?? FALLBACK_PLATFORM
      } catch {
        return FALLBACK_PLATFORM
      }
    },
    { default: () => FALLBACK_PLATFORM },
  )

  // After hydration, so a change in the platform admin shows without a rebuild (as usePlans).
  onNuxtReady(() => refresh())

  return computed(() => data.value)
}

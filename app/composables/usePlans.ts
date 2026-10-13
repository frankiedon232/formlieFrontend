/**
 * The plans from GET {API}/public/plans (docs/API-HOOKS.md). Read while the page is prerendered and again in the
 * browser, so a price the owner changes shows without a rebuild. When the API doesn't answer, the sample plans
 * (app/data/plans.json) are used and `source` says so.
 */
export function usePlans() {
  const links = useSiteLinks()

  const { data, refresh } = useAsyncData(
    'plans',
    async () => {
      try {
        const answer = await $fetch(links.api('public/plans'), { timeout: 5000, retry: 0 })
        const plans = parsePlans(answer)
        if (plans) return { plans, source: 'api' as PlansSource }
      } catch {
        // Falls through to the samples.
      }
      return { plans: fallbackPlans(), source: 'fallback' as PlansSource }
    },
    { default: () => ({ plans: fallbackPlans(), source: 'fallback' as PlansSource }) },
  )

  // Fresh prices in the browser (the API allows any origin and caches for 5 minutes).
  // After hydration: during it, refresh() would return the prerendered copy from the payload instead of fetching.
  onNuxtReady(() => refresh())

  const plans = computed(() => data.value.plans)
  const source = computed(() => data.value.source)
  const plan = (id: Plan['id']) => plans.value.find(item => item.id === id)

  return { plans, source, plan }
}

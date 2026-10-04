/**
 * In-app navigation feedback (owner, 2026-10-02): the top bar and the in-page sweeping bar start
 * the moment a link is clicked, not only on a full reload, and keep running until the new page
 * has fetched its first data. Query-only changes (filters, paging, sort) are covered by the API
 * calls they trigger, so only path changes count as navigation here.
 */
export default defineNuxtPlugin(nuxtApp => {
  const router = useRouter()
  const activity = useActivity()
  let end: (() => void) | null = null

  router.beforeEach((to, from) => {
    if (to.path === from.path || end) return
    end = activity.begin({ immediate: true })
  })

  const settle = () => {
    if (!end) return
    const done = end
    end = null
    // Give the new page a moment to mount and start its requests, so the bar runs straight
    // through to the data arriving instead of stopping and starting again.
    setTimeout(done, 120)
  }

  router.afterEach(settle)
  router.onError(settle)
  nuxtApp.hook('app:error', settle)
})

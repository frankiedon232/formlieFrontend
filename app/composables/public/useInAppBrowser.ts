/**
 * In-app browser for public forms (owner, 2026-10-03): links on a form page (website, terms,
 * privacy) open in a window over the form instead of leaving it, so nothing typed in is lost.
 * One window per page; client-only state (never set during server rendering).
 */
const state = reactive({ open: false, url: '', title: '' })

export function useInAppBrowser() {
  function open(url: string, title?: string) {
    if (!/^https:\/\//i.test(url)) return
    state.url = url
    state.title = title ?? ''
    state.open = true
  }
  const close = () => (state.open = false)
  return { state, open, close }
}

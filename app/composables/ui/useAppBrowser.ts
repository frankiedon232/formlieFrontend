/**
 * The app's browser window (owner 2026-10-10): like the one on public forms, a window over the page that shows
 * a page without leaving the app. Formalie's own forms open in it (Contact support, Enterprise enquiry: we
 * collect our own data with our own forms), filled in with what the app knows through the address.
 */
import type { PlatformForm } from '#shared/utils/platform/forms'
import { PLATFORM_FORMS } from '#shared/utils/platform/forms'
import { formLink, publicHosts } from '#shared/utils/urls/public'

const state = reactive({ open: false, url: '', title: '', form: null as string | null })

export function useAppBrowser() {
  const config = useRuntimeConfig()

  function open(url: string, title = '', form: string | null = null) {
    state.url = url
    state.title = title
    state.form = form
    state.open = true
  }
  const close = () => (state.open = false)

  /** The address of one of Formalie's forms (its embed page), with starting values for the fields that take them. */
  function formUrl(form: PlatformForm, values: Record<string, string | null | undefined> = {}) {
    const key = PLATFORM_FORMS[form]
    // Development on localhost has no forms host: the same address serves the form pages
    const local = import.meta.dev && /^(localhost|127\.0\.0\.1|\d+\.\d+\.\d+\.\d+)$/.test(location.hostname)
    const base = local ? `${location.origin}/${key}/embed` : formLink(publicHosts(config.public, location.port), key, 'embed')
    const query = new URLSearchParams(Object.entries(values).filter((entry): entry is [string, string] => !!entry[1]))
    return query.size ? `${base}?${query}` : base
  }

  function openForm(form: PlatformForm, title: string, values: Record<string, string | null | undefined> = {}) {
    open(formUrl(form, values), title, PLATFORM_FORMS[form])
  }
  return { state, open, close, formUrl, openForm }
}

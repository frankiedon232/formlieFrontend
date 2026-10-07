/**
 * Organisations in the workspace (F14 M7): the list for the rail's switcher and Settings, and the one
 * the person narrowed the portal to (remembered in this browser per workspace; not secret). Every API
 * call carries it (useApi), so forms, responses, analytics and counts follow. Switching reloads the page.
 */
import type { Organisation } from '#shared/types/organisations'

const list = ref<Organisation[] | null>(null)
/** The chosen organisation's id, or null for all. Read by useApi for every request. */
export const currentOrganisation = ref<string | null>(null)
let loading: Promise<void> | null = null

/** Two or three letters for an organisation: the first word of its short name, else the initials of its name. */
export const organisationInitials = (org: Pick<Organisation, 'name' | 'short_name'>) =>
  (org.short_name ? (org.short_name.split(/\s+/)[0] ?? '').slice(0, 3) : org.name.split(/\s+/).map(part => part[0]).join('').slice(0, 2)).toUpperCase()

const storageKey = (subdomain: string) => `formalie:organisation:${subdomain}`

export function useOrganisations() {
  const api = useApi()
  const tenant = useTenant()

  /** Restore the choice for this workspace (before the first lists load). */
  function restore() {
    const subdomain = tenant.profile.value?.subdomain
    if (!subdomain || import.meta.server) return
    try {
      currentOrganisation.value = localStorage.getItem(storageKey(subdomain))
    } catch {
      currentOrganisation.value = null
    }
  }
  function load(force = false) {
    if (loading && !force) return loading
    loading = api
      .get<Organisation[]>('/organisations', undefined, { background: true })
      .then(result => {
        list.value = result.data
        // A choice that no longer exists (or was archived) falls back to all
        if (currentOrganisation.value && !result.data.some(item => item.id === currentOrganisation.value && item.status === 'active')) choose(null, false)
      })
      .catch(() => {
        loading = null
      })
    return loading
  }
  function choose(id: string | null, reload = true) {
    const subdomain = tenant.profile.value?.subdomain
    currentOrganisation.value = id
    try {
      if (subdomain && id) localStorage.setItem(storageKey(subdomain), id)
      else if (subdomain) localStorage.removeItem(storageKey(subdomain))
    } catch {
      // private mode: the choice lasts until the page is reloaded
    }
    if (reload) window.location.reload()
  }
  const active = computed(() => (list.value ?? []).filter(item => item.status === 'active'))
  const current = computed(() => active.value.find(item => item.id === currentOrganisation.value) ?? null)
  const several = computed(() => active.value.length > 1)
  return { list, active, current, several, currentId: currentOrganisation, restore, load, choose }
}

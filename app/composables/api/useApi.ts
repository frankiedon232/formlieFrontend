import { ORGANISATION_HEADER } from '#shared/types/organisations'
import type { ApiSuccess, ListMeta } from '#shared/types/api'
import type { AuthTokens } from '#shared/types/auth'
import type { ApiClient, HttpMethod, RequestOptions } from '~/utils/api/client'

/**
 * The only way to call the API (CLAUDE.md rule 10). Wraps the framework-free client
 * (utils/api/client.ts) with the runtime base URL, the in-memory session token, token refresh
 * and a real fetch. Client-only: SSR public forms use a server-side fetch (decision 14).
 *
 *   const api = useApi()
 *   const { data, meta } = await api.list<Form>('/forms', { page: 1 })
 *   await api.post('/forms', { name })
 */
let client: ApiClient | null = null

// Every request (except background polling) counts as activity: top bar + in-page bar
// (useActivity, CLAUDE.md rule 5). The top bar throttles itself, so very fast calls never flash.
let activity: ReturnType<typeof useActivity> | null = null

function track<T>(work: () => Promise<T>, background?: boolean): Promise<T> {
  if (background || !activity) return work()
  return work().finally(activity.begin())
}

function getClient(): ApiClient {
  if (import.meta.server) {
    throw new Error('useApi() is client-only. Server-rendered pages use a server-side fetch.')
  }
  if (client) return client

  const config = useRuntimeConfig()
  const session = useSession()
  const devTenant = useState<string | null>('tenant:dev', () => null)
  const router = useRouter()
  activity = useActivity()

  client = createApiClient({
    baseUrl: config.public.apiBase,
    transport: async (url, init) => {
      const response = await fetch(url, { ...init, credentials: 'same-origin', cache: 'no-store' })
      return { status: response.status, json: await response.json().catch(() => null) }
    },
    getAccessToken: () => session.accessToken.value,
    // Dev only: tenant chosen with ?tenant= on localhost / LAN IP (decision 19). The mock honours it.
    getExtraHeaders: (): Record<string, string> => ({
      ...(import.meta.dev && devTenant.value ? { 'x-formalie-dev-tenant': devTenant.value } : {}),
      // The organisation chosen in the rail narrows lists (F14 M7)
      ...(currentOrganisation.value ? { [ORGANISATION_HEADER]: currentOrganisation.value } : {}),
    }),
    refreshAccessToken: async () => {
      try {
        const { data } = await client!.request<AuthTokens>('POST', '/auth/refresh', { skipAuthRefresh: true })
        session.applyTokens(data)
        return true
      } catch {
        return false
      }
    },
    onUnauthenticated: () => {
      const wasSignedIn = session.isAuthenticated.value
      session.clear()
      const route = router.currentRoute.value
      if (wasSignedIn && route.meta.auth !== 'guest' && route.meta.auth !== false) {
        router.replace({ path: '/auth/login', query: { expired: '1', redirect: route.fullPath } })
      }
    },
  })
  return client
}

export function useApi() {
  const call = <T>(method: HttpMethod, path: string, options?: RequestOptions) => {
    const api = getClient()
    return track(() => api.request<T>(method, path, options), options?.background)
  }

  return {
    request: call,
    get: <T>(path: string, query?: Record<string, unknown>, options?: RequestOptions) =>
      call<T>('GET', path, { ...options, query }),
    post: <T>(path: string, body?: unknown, options?: RequestOptions) =>
      call<T>('POST', path, { ...options, body }),
    put: <T>(path: string, body?: unknown, options?: RequestOptions) =>
      call<T>('PUT', path, { ...options, body }),
    patch: <T>(path: string, body?: unknown, options?: RequestOptions) =>
      call<T>('PATCH', path, { ...options, body }),
    del: <T>(path: string, options?: RequestOptions) => call<T>('DELETE', path, options),
    /** Paginated list endpoint → `{ data, meta }` (API-CONTRACT "Lists"). */
    list: async <T>(path: string, query?: Record<string, unknown>, options?: RequestOptions) => {
      const response = (await call<T[]>('GET', path, { ...options, query })) as unknown as ApiSuccess<
        T[],
        ListMeta
      >
      return { data: response.data, meta: response.meta }
    },
    /** Drop the secure session (logout, tenant switch); the next call re-handshakes. */
    resetSecureSession: () => client?.resetSecureSession(),
  }
}

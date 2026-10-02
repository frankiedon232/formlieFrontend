import type { ApiSuccess, ListMeta } from '#shared/types/api'
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

function getClient(): ApiClient {
  if (import.meta.server) {
    throw new Error('useApi() is client-only. Server-rendered pages use a server-side fetch.')
  }
  if (client) return client

  const config = useRuntimeConfig()
  const session = useSession()

  client = createApiClient({
    baseUrl: config.public.apiBase,
    transport: async (url, init) => {
      const response = await fetch(url, { ...init, credentials: 'same-origin', cache: 'no-store' })
      return { status: response.status, json: await response.json().catch(() => null) }
    },
    getAccessToken: () => session.accessToken.value,
    refreshAccessToken: async () => {
      try {
        const { data } = await client!.request<{ access_token: string; expires_in?: number }>(
          'POST',
          '/auth/refresh',
          { skipAuthRefresh: true },
        )
        session.setAccessToken(data.access_token, data.expires_in)
        return true
      } catch {
        return false
      }
    },
    onUnauthenticated: () => {
      session.clear()
      // F3: redirect to /auth/login with a "session expired" notice.
    },
  })
  return client
}

export function useApi() {
  const call = <T>(method: HttpMethod, path: string, options?: RequestOptions) =>
    getClient().request<T>(method, path, options)

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

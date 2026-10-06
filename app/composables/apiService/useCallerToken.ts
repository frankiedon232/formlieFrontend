/**
 * The token an endpoint's examples show (owner, 2026-10-06: "most modern systems do this"): one of the
 * workspace's own tokens that may call it, masked (its prefix and last four), so the example reads like
 * the real call and says which token to take from Tokens & headers. Prefers a token limited to the
 * endpoint, then to its service, then one for everything; live before test; a bearer token before a
 * client id and secret. Also tells how an endpoint signs in: a token is one kind or the other, never
 * both (owner, 2026-10-06), so examples show the /token step for client tokens. Loaded once and shared.
 */
import type { ApiToken } from '#shared/types/apiService'
import { scopeAllows } from '#shared/utils/apiService/tokens'
import type { ApiMethod } from '#shared/utils/urls/public'

const tokens = ref<ApiToken[] | null>(null)
let loading: Promise<void> | null = null
type Target = { id: string; service: { id: string } }

export function useCallerToken() {
  const api = useApi()
  function load(force = false) {
    if (loading && !force) return loading
    loading = api
      .list<ApiToken>('/api-tokens', { page_size: 100, sort: 'name' }, { background: true })
      .then(result => void (tokens.value = result.data))
      .catch(() => void (tokens.value = []))
    return loading
  }
  const usable = (endpoint: Target, methods: ApiMethod[]) =>
    (tokens.value ?? []).filter(token => token.kind !== 'webhook' && (token.status === 'active' || token.status === 'expiring') && methods.some(method => scopeAllows(token.scopes, { endpoint_id: endpoint.id, service_id: endpoint.service.id, method })))
  const rank = (endpoint: Target, token: ApiToken) => (token.scopes.endpoints.includes(endpoint.id) ? 0 : token.scopes.services.includes(endpoint.service.id) ? 4 : 8) + (token.mode === 'live' ? 0 : 2) + (token.kind === 'static' ? 0 : 1)
  /** The best token for this endpoint and method, or null when none may call it. */
  function pick(endpoint: Target, method: ApiMethod): ApiToken | null {
    return usable(endpoint, [method]).sort((a, b) => rank(endpoint, a) - rank(endpoint, b))[0] ?? null
  }
  /** The tokens that may call it, by how they sign in. */
  function kindsFor(endpoint: Target, methods: ApiMethod[]): Record<'static' | 'client', ApiToken[]> {
    const list = usable(endpoint, methods).sort((a, b) => rank(endpoint, a) - rank(endpoint, b))
    return { static: list.filter(token => token.kind === 'static'), client: list.filter(token => token.kind === 'client') }
  }
  return { tokens, load, pick, kindsFor }
}

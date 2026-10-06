/**
 * The token an endpoint's examples show (owner, 2026-10-06: "most modern systems do this"): one of the
 * workspace's own tokens that may call it, masked (its prefix and last four), so the example reads like
 * the real call and says which token to take from Tokens & headers. Prefers a token limited to the
 * endpoint, then to its service, then one for everything; live before test. Bearer tokens only (a
 * client id + secret pair signs in first). Loaded once and shared.
 */
import type { ApiToken } from '#shared/types/apiService'
import { scopeAllows } from '#shared/utils/apiService/tokens'
import type { ApiMethod } from '#shared/utils/urls/public'

const tokens = ref<ApiToken[] | null>(null)
let loading: Promise<void> | null = null

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
  /** The best token for this endpoint and method, or null when none may call it. */
  function pick(endpoint: { id: string; service: { id: string } }, method: ApiMethod): ApiToken | null {
    const usable = (tokens.value ?? []).filter(token => token.kind === 'static' && (token.status === 'active' || token.status === 'expiring') && scopeAllows(token.scopes, { endpoint_id: endpoint.id, service_id: endpoint.service.id, method }))
    const rank = (token: ApiToken) => (token.scopes.endpoints.includes(endpoint.id) ? 0 : token.scopes.services.includes(endpoint.service.id) ? 2 : 4) + (token.mode === 'live' ? 0 : 1)
    return usable.sort((a, b) => rank(a) - rank(b))[0] ?? null
  }
  return { tokens, load, pick }
}

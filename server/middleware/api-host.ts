/**
 * `https://api.formalie.dev:2202/{apiKey}/{endpoint}` in development (a hosts entry for
 * api.formalie.dev): the same addresses as production (F13).
 *   mock on  → answered by the mock public API
 *   mock off → passed to the backend, whose main app hands the api.* host to the API service gateway
 *              (formlyBackend app/gateway.py), so Postman keeps using the :2202 address (2026-10-12)
 * In production Nginx sends api.formalie.com straight to the gateway; this never runs there.
 */
import { handlePublicApi } from '../mock/publicApi'

export default defineEventHandler(event => {
  const host = getRequestHost(event, { xForwardedHost: false })
  if (host.split(':')[0] !== 'api.formalie.dev') return
  const config = useRuntimeConfig(event)
  if (config.public.apiMock) return handlePublicApi(event, event.path.split('?')[0]!)
  return proxyRequest(event, `${config.apiProxyTarget.replace(/\/$/, '')}${event.path}`, {
    headers: {
      'x-forwarded-host': host,
      'x-forwarded-proto': getRequestProtocol(event),
      'x-forwarded-for': getRequestIP(event, { xForwardedFor: true }) ?? '',
    },
    // The gateway's answers (CORS preflights, redirects) go back to the caller as they are
    fetchOptions: { redirect: 'manual' },
  })
})

/**
 * Dev proxy /api/** → FastAPI (NUXT_PUBLIC_API_MOCK=false).
 * Forwards the original host so the backend TenantMiddleware can read the subdomain.
 * In production Nginx routes /api before it ever reaches Nuxt.
 */
export default defineEventHandler(event => {
  const { apiProxyTarget } = useRuntimeConfig(event)
  const host = getRequestHost(event, { xForwardedHost: false })

  return proxyRequest(event, `${apiProxyTarget.replace(/\/$/, '')}${event.path}`, {
    headers: {
      'x-forwarded-host': host,
      'x-forwarded-proto': getRequestProtocol(event),
    },
  })
})

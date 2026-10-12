/**
 * Dev proxy /api/** → FastAPI (NUXT_PUBLIC_API_MOCK=false).
 * Forwards the original host and the visitor's IP so the backend TenantMiddleware can read the subdomain.
 * In production Nginx routes /api before it ever reaches Nuxt.
 */
export default defineEventHandler(event => {
  const { apiProxyTarget } = useRuntimeConfig(event)
  const host = getRequestHost(event, { xForwardedHost: false })

  return proxyRequest(event, `${apiProxyTarget.replace(/\/$/, '')}${event.path}`, {
    headers: {
      'x-forwarded-host': host,
      'x-forwarded-proto': getRequestProtocol(event),
      // The visitor's address: without it every request reaches the backend as 127.0.0.1, so per-address
      // rate limits, audit IPs and the request log would all see the proxy instead of the person.
      'x-forwarded-for': getRequestIP(event, { xForwardedFor: true }) ?? '',
    },
    // Redirects go back to the browser (social sign-in sends it to Google, Microsoft or Facebook); following
    // them here would load the provider's page under our address and break the sign-in.
    fetchOptions: { redirect: 'manual' },
  })
})

/**
 * Short links for the server-rendered `/s/{code}` page (F10 M3): where the code leads. Same rules as
 * the public-forms internal route — only the Nuxt server itself may call it (server-only token).
 *   mock on  → the mock data (the visit is counted there)
 *   mock off → the API's internal endpoint, service to service
 */
import { SHORT_CODE_PATTERN } from '#shared/utils/urls/public'

const INTERNAL_TOKEN_HEADER = 'x-formalie-internal'

export default defineEventHandler(async event => {
  const config = useRuntimeConfig(event)
  if (!config.internalToken || getHeader(event, INTERNAL_TOKEN_HEADER) !== config.internalToken) {
    setResponseStatus(event, 403)
    return { error: { code: 'FRM-PERM-1001' } }
  }
  const code = getRouterParam(event, 'code') ?? ''
  if (!SHORT_CODE_PATTERN.test(code)) {
    setResponseStatus(event, 404)
    return { error: { code: 'FRM-FORM-1001' } }
  }

  if (!config.public.apiMock) {
    try {
      const data = await $fetch<{ target: string }>(`${config.apiProxyTarget}/api/v1/internal/short/${encodeURIComponent(code)}`, {
        headers: { [INTERNAL_TOKEN_HEADER]: config.internalToken, 'x-forwarded-host': getRequestHost(event, { xForwardedHost: true }) },
      })
      return { data }
    } catch (error) {
      const status = (error as { statusCode?: number }).statusCode ?? 502
      setResponseStatus(event, status)
      return { error: { code: status === 404 ? 'FRM-FORM-1001' : 'FRM-GEN-5000' } }
    }
  }

  const [{ resolveShortLink }, { MockError }] = await Promise.all([import('../../../mock/routes/publicForms'), import('../../../mock/core/respond')])
  try {
    return { data: { target: resolveShortLink(event, code) } }
  } catch (error) {
    const failure = error instanceof MockError ? error.code : 'FRM-GEN-5000'
    setResponseStatus(event, failure === 'FRM-FORM-1001' ? 404 : 500)
    return { error: { code: failure } }
  }
})

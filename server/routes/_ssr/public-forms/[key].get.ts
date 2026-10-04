/**
 * Secure server-side fetch for server-rendered public form pages (F10). Only the Nuxt server itself
 * may call it: the request must carry the server-only internal token (runtimeConfig.internalToken,
 * never sent to browsers). The page asks for the published form while rendering, so respondents
 * get the whole form in the first response (fast first paint, readable by search engines).
 *   mock on  → reads the mock data directly
 *   mock off → asks the API's internal endpoint with the same token (service-to-service)
 */
import type { PublicForm } from '#shared/types/public'
import { isFormAddress } from '#shared/utils/urls/public'

export const INTERNAL_TOKEN_HEADER = 'x-formalie-internal'

export default defineEventHandler(async event => {
  const config = useRuntimeConfig(event)
  const token = getHeader(event, INTERNAL_TOKEN_HEADER)
  if (!config.internalToken || token !== config.internalToken) {
    setResponseStatus(event, 403)
    return { error: { code: 'FRM-PERM-1001' } }
  }
  const key = getRouterParam(event, 'key') ?? ''
  if (!isFormAddress(key)) {
    setResponseStatus(event, 404)
    return { error: { code: 'FRM-FORM-1001' } }
  }

  if (!config.public.apiMock) {
    try {
      const data = await $fetch<PublicForm>(`${config.apiProxyTarget}/api/v1/internal/public-forms/${encodeURIComponent(key)}`, {
        // The respondent's cookies go along: an unlocked password form stays unlocked (F10 M3).
        headers: { [INTERNAL_TOKEN_HEADER]: config.internalToken, 'x-forwarded-host': getRequestHost(event, { xForwardedHost: true }), cookie: getHeader(event, 'cookie') ?? '' },
      })
      return { data }
    } catch (error) {
      const status = (error as { statusCode?: number }).statusCode ?? 502
      setResponseStatus(event, status)
      return { error: { code: status === 404 ? 'FRM-FORM-1001' : 'FRM-GEN-5000' } }
    }
  }

  const [{ publicFormView }, { MockError }, { encodeIds }] = await Promise.all([
    import('../../../mock/routes/publicForms'),
    import('../../../mock/core/respond'),
    import('../../../mock/core/ids'),
  ])
  try {
    return { data: encodeIds(publicFormView(event, key)) }
  } catch (error) {
    const code = error instanceof MockError ? error.code : 'FRM-GEN-5000'
    setResponseStatus(event, code === 'FRM-FORM-1001' ? 404 : 500)
    return { error: { code } }
  }
})

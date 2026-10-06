/**
 * `https://api.formalie.dev:2202/{apiKey}/{endpoint}` in development (a hosts entry for
 * api.formalie.dev): the same addresses as production, answered by the mock public API (F13).
 */
import { handlePublicApi } from '../mock/publicApi'

export default defineEventHandler(event => {
  const host = (getRequestHost(event, { xForwardedHost: true }) ?? '').split(':')[0]
  if (host !== 'api.formalie.dev' || !useRuntimeConfig().public.apiMock) return
  return handlePublicApi(event, event.path.split('?')[0]!)
})

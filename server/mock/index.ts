/**
 * Mock API entry (NUXT_PUBLIC_API_MOCK=true). Mounted at /api/** by nuxt.config.ts.
 * Shapes follow docs/API-CONTRACT.md exactly; add one file per domain in ./routes.
 */
import { fail } from './core/respond'
import { listFolders, listForms } from './routes/forms'
import { csrf, handshake, health } from './routes/system'

const router = createRouter()
  .get('/health', health)
  .post('/crypto/handshake', handshake)
  .get('/auth/csrf', csrf)
  .get('/forms', listForms)
  .get('/folders', listFolders)
  .use(
    '/**',
    defineEventHandler(event => {
      const reply = fail('FRM-GEN-1004')
      setResponseStatus(event, reply.status)
      return reply.body
    }),
  )

const v1 = useBase('/api/v1', router.handler)

export default defineEventHandler(event => {
  event.context.fullPath = event.path.split('?')[0]
  // Small artificial latency so loading states are visible during development.
  return new Promise(resolve => setTimeout(resolve, 150)).then(() => v1(event))
})

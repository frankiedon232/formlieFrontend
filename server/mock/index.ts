/**
 * Mock API entry (NUXT_PUBLIC_API_MOCK=true). Mounted at /api/** by nuxt.config.ts.
 * Shapes follow docs/API-CONTRACT.md exactly; add one file per domain in ./routes.
 */
import { fail } from './core/respond'
import * as auth from './routes/auth'
import { listFolders, listForms } from './routes/forms'
import { csrf, handshake, health } from './routes/system'
import * as tenants from './routes/tenants'

const router = createRouter()
  // system
  .get('/health', health)
  .post('/crypto/handshake', handshake)
  .get('/auth/csrf', csrf)
  // tenants
  .get('/tenants/public', tenants.publicProfile)
  .get('/tenants/subdomain-availability', tenants.subdomainAvailability)
  .post('/tenants/find-workspace', tenants.findWorkspace)
  .post('/tenants/find-workspace/verify', tenants.findWorkspaceVerify)
  // auth
  .post('/auth/login', auth.login)
  .post('/auth/otp/verify', auth.verifyOtp)
  .post('/auth/otp/resend', auth.resendOtp)
  .post('/auth/refresh', auth.refresh)
  .post('/auth/logout', auth.logout)
  .post('/auth/signup', auth.signup)
  .post('/auth/signup/complete', auth.signupComplete)
  .post('/auth/exchange-ticket', auth.exchangeTicket)
  .post('/auth/password/forgot', auth.forgotPassword)
  .post('/auth/password/reset', auth.resetPassword)
  .get('/auth/oauth/:provider/start', auth.oauthStart)
  .get('/me', auth.me)
  // forms
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

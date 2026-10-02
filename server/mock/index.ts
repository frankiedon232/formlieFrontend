/**
 * Mock API entry (NUXT_PUBLIC_API_MOCK=true). Mounted at /api/** by nuxt.config.ts.
 * Shapes follow docs/API-CONTRACT.md exactly; add one file per domain in ./routes.
 */
import { fail } from './core/respond'
import * as audit from './routes/audit'
import * as auth from './routes/auth'
import * as forms from './routes/forms'
import { navigationCounts } from './routes/navigation'
import * as onboarding from './routes/onboarding'
import * as uploads from './routes/uploads'
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
  .get('/forms', forms.listForms)
  .post('/forms', forms.createForm)
  .get('/forms/facets', forms.formFacets)
  .post('/forms/import', forms.importForm)
  .post('/forms/bulk', forms.bulkForms)
  .delete('/forms/trash', forms.emptyTrash)
  .get('/forms/:id', forms.getForm)
  .patch('/forms/:id', forms.patchForm)
  .delete('/forms/:id', forms.deleteForm)
  .post('/forms/:id/duplicate', forms.duplicateForm)
  .post('/forms/:id/:action', forms.formLifecycle)
  .get('/folders', forms.listFolders)
  .post('/folders', forms.createFolder)
  .patch('/folders/:id', forms.renameFolder)
  .delete('/folders/:id', forms.deleteFolder)
  .get('/navigation/counts', navigationCounts)
  // onboarding + uploads
  .get('/onboarding', onboarding.getOnboarding)
  .patch('/onboarding', onboarding.patchOnboarding)
  .post('/onboarding/finish', onboarding.finishOnboarding)
  .post('/uploads', uploads.createUpload)
  .post('/uploads/:id/complete', uploads.completeUpload)
  .put('/storage/:token', uploads.storeUpload)
  .get('/files/:id', uploads.serveFile)
  // audit trail
  .get('/audit-logs', audit.listAuditLogs)
  .get('/audit-logs/facets', audit.auditFacets)
  .post('/audit-logs/export', audit.exportAuditLogs)
  .get('/audit-logs/:id', audit.getAuditLog)
  .get('/exports/:id', audit.getExportJob)
  .get('/downloads/:token', audit.download)
  .use(
    '/**',
    defineEventHandler(event => {
      const reply = fail('FRM-GEN-1004')
      setResponseStatus(event, reply.status)
      return reply.body
    }),
  )

/** Above the top bar's 200 ms throttle, like a real network, so progress is visible while testing. */
const MOCK_LATENCY_MS = 350

const v1 = useBase('/api/v1', router.handler)

export default defineEventHandler(event => {
  event.context.fullPath = event.path.split('?')[0]
  event.context.requestId = crypto.randomUUID()
  // Realistic latency (like a real network) so loading states are visible during development.
  return new Promise(resolve => setTimeout(resolve, MOCK_LATENCY_MS)).then(() => v1(event))
})

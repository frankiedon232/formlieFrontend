/**
 * Mock API entry (NUXT_PUBLIC_API_MOCK=true). Mounted at /api/** by nuxt.config.ts.
 * Shapes follow docs/API-CONTRACT.md exactly; add one file per domain in ./routes.
 */
import { fail } from './core/respond'
import * as audit from './routes/audit'
import { getDirectory } from './routes/directory'
import { getFormOverview } from './routes/formOverview'
import * as responses from './routes/responses'
import * as analytics from './routes/analytics'
import * as apiService from './routes/apiService'
import * as apiAccess from './routes/apiAccess'
import * as apiTraffic from './routes/apiTraffic'
import * as apiDocs from './routes/apiDocs'
import * as responseExports from './routes/responseExports'
import * as folders from './routes/folders'
import * as dataSources from './routes/dataSources'
import * as destinations from './routes/destinations'
import * as explorer from './routes/explorer'
import * as explorerSchema from './routes/explorerSchema'
import * as query from './routes/query'
import * as savedQueries from './routes/savedQueries'
import * as dataActivity from './routes/dataActivity'
import * as responseFiles from './routes/responseFiles'
import * as publicForms from './routes/publicForms'
import * as templates from './routes/templates'
import * as auth from './routes/auth'
import * as formDraft from './routes/formDraft'
import * as library from './routes/library'
import * as themes from './routes/themes'
import * as pageDesigns from './routes/pageDesigns'
import * as formShare from './routes/formShare'
import * as formInvites from './routes/formInvites'
import * as forms from './routes/forms'
import { navigationCounts } from './routes/navigation'
import * as onboarding from './routes/onboarding'
import * as uploads from './routes/uploads'
import { csrf, handshake, health } from './routes/system'
import * as tenants from './routes/tenants'
import * as webhooks from './routes/webhooks'

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
  .post('/forms/pass', formInvites.formPass)
  .post('/forms/import', forms.importForm)
  .post('/forms/bulk', forms.bulkForms)
  .delete('/forms/trash', forms.emptyTrash)
  .get('/forms/:id', forms.getForm)
  .get('/forms/:id/overview', getFormOverview)
  .patch('/forms/:id', forms.patchForm)
  .get('/forms/:id/share', formShare.getShare)
  .put('/forms/:id/share', formShare.saveShare)
  .get('/forms/:id/share/link-check', formShare.checkLink)
  .post('/forms/:id/short-link', formShare.createShortLink)
  .delete('/forms/:id/short-link', formShare.removeShortLink)
  .get('/forms/:id/invites', formInvites.listInvites)
  .post('/forms/:id/invites', formInvites.createInvites)
  .post('/forms/:id/invites/:inviteId/resend', formInvites.resendInvite)
  .delete('/forms/:id/invites/:inviteId', formInvites.revokeInvite)
  .delete('/forms/:id', forms.deleteForm)
  .post('/forms/:id/duplicate', forms.duplicateForm)
  .get('/forms/:id/builder', formDraft.getBuilder)
  .get('/forms/:id/preview', formDraft.previewForm)
  .get('/forms/:id/responses', responses.listFormResponses)
  .get('/forms/:id/responses/insights', responses.formInsights)
  .get('/forms/:id/responses/tags', responses.formResponseTags)
  .get('/responses/insights', responses.inboxInsights)
  .get('/analytics/overview', analytics.analyticsOverview)
  .get('/api-service/settings', apiService.apiSettings)
  .get('/api-service/setup', apiService.apiSetup)
  .post('/api-service/key/rotate', apiService.rotateApiKey)
  .get('/api-service/limits', apiAccess.getRateLimits)
  .get('/api-logs', apiTraffic.listApiLogs)
  .get('/api-logs/insights', apiTraffic.apiLogInsights)
  .get('/api-logs/settings', apiTraffic.getApiLogSettings)
  .put('/api-logs/settings', apiTraffic.updateApiLogSettings)
  .get('/api-logs/:id', apiTraffic.getApiLog)
  .get('/api-analytics', apiTraffic.apiAnalytics)
  .put('/api-service/limits', apiAccess.updateRateLimits)
  .get('/api-access-rules', apiAccess.listAccessRules)
  .get('/api-access-rules/insights', apiAccess.accessInsights)
  .post('/api-access-rules', apiAccess.createAccessRule)
  .post('/api-access-rules/test', apiAccess.testAccess)
  .get('/api-access-rules/:id', apiAccess.getAccessRule)
  .patch('/api-access-rules/:id', apiAccess.updateAccessRule)
  .delete('/api-access-rules/:id', apiAccess.deleteAccessRule)
  .get('/api-tokens', apiService.listApiTokens)
  .get('/api-tokens/insights', apiService.apiTokenInsights)
  .post('/api-tokens', apiService.createApiToken)
  .get('/api-tokens/:id', apiService.getApiToken)
  .patch('/api-tokens/:id', apiService.updateApiToken)
  .delete('/api-tokens/:id', apiService.deleteApiToken)
  .post('/api-tokens/:id/rotate', apiService.rotateApiToken)
  .post('/api-tokens/:id/revoke', apiService.revokeApiToken)
  .post('/api-tokens/:id/reveal', apiService.revealApiToken)
  .get('/api-services', apiService.listApiServices)
  .get('/api-services/insights', apiService.apiServiceInsights)
  .post('/api-services', apiService.createApiService)
  .get('/api-services/:id', apiService.getApiService)
  .patch('/api-services/:id', apiService.updateApiService)
  .delete('/api-services/:id', apiService.deleteApiService)
  .post('/api-services/:id/duplicate', apiService.duplicateApiService)
  .get('/api-endpoints', apiService.listApiEndpoints)
  .get('/api-endpoints/insights', apiService.apiEndpointInsights)
  .get('/api-endpoints/form-fields', apiService.apiEndpointFormFields)
  .post('/api-endpoints', apiService.createApiEndpoint)
  .get('/api-endpoints/:id', apiService.getApiEndpoint)
  .post('/api-endpoints/:id/try', apiDocs.tryEndpoint)
  .get('/webhooks', webhooks.listWebhooks)
  .get('/webhooks/insights', webhooks.webhookInsights)
  .post('/webhooks', webhooks.createWebhook)
  .get('/webhooks/:id', webhooks.getWebhook)
  .patch('/webhooks/:id', webhooks.updateWebhook)
  .delete('/webhooks/:id', webhooks.deleteWebhook)
  .post('/webhooks/:id/rotate', webhooks.rotateWebhookSecret)
  .post('/webhooks/:id/test', webhooks.testWebhook)
  .post('/webhooks/:id/reveal', webhooks.revealWebhookSecret)
  .get('/webhook-deliveries', webhooks.listDeliveries)
  .get('/webhook-deliveries/:id', webhooks.getDelivery)
  .post('/webhook-deliveries/:id/resend', webhooks.resendDelivery)
  .patch('/api-endpoints/:id', apiService.updateApiEndpoint)
  .delete('/api-endpoints/:id', apiService.deleteApiEndpoint)
  .get('/analytics/forms', analytics.analyticsForms)
  .get('/analytics/forms/:id/funnel', analytics.formFunnel)
  .get('/responses/forms', responses.listResponseForms)
  .post('/responses/bulk', responses.bulkResponses)
  .post('/forms/:id/responses/export', responseExports.exportFormResponses)
  .get('/responses/exports', responseExports.listResponseExports)
  .get('/responses/exports/:id', responseExports.getResponseExport)
  .post('/responses/exports/:id/link', responseExports.responseExportLink)
  .delete('/responses/exports/:id', responseExports.deleteResponseExport)
  .get('/response-exports/:token', responseExports.downloadResponseExport)
  .get('/responses', responses.listResponses)
  .get('/responses/:id', responses.getResponse)
  .patch('/responses/:id', responses.patchResponse)
  .delete('/responses/:id', responses.deleteResponse)
  .post('/responses/:id/notes', responses.addNote)
  .post('/responses/:id/files', responseFiles.fileLink)
  .get('/response-files/:token', responseFiles.serveResponseFile)
  .put('/forms/:id/draft', formDraft.saveDraft)
  .post('/forms/:id/publish', formDraft.publishForm)
  .post('/forms/:id/discard', formDraft.discardDraft)
  .get('/forms/:id/versions', formDraft.listVersions)
  .get('/forms/:id/versions/:vid', formDraft.getVersion)
  .post('/forms/:id/versions/:vid/restore', formDraft.restoreVersion)
  .post('/forms/:id/:action', forms.formLifecycle)
  .get('/folders', forms.listFolders)
  .get('/folders/overview', folders.folderOverview)
  .get('/folders/:id', folders.getFolder)
  .post('/folders', forms.createFolder)
  .patch('/folders/:id', forms.renameFolder)
  .delete('/folders/:id', forms.deleteFolder)
  // data sources (F12)
  .get('/datasources', dataSources.listDataSources)
  .get('/datasources/insights', dataSources.dataSourceInsights)
  .get('/datasources/meta', dataSources.dataSourceMeta)
  .post('/datasources/test', dataSources.startConnectionTest)
  .get('/datasources/tests/:id', dataSources.getConnectionTest)
  .post('/datasources', dataSources.createDataSource)
  .get('/datasources/:id', dataSources.getDataSource)
  .patch('/datasources/:id', dataSources.patchDataSource)
  .post('/datasources/:id/test', dataSources.testSavedConnection)
  .post('/datasources/:id/duplicate', dataSources.duplicateDataSource)
  .get('/datasources/:id/tables', destinations.listTables)
  .get('/datasources/:id/explorer/tables', explorer.explorerTables)
  .post('/datasources/:id/explorer/tables', explorerSchema.createTable)
  .post('/datasources/:id/explorer/changes', explorerSchema.changeTable)
  .post('/datasources/:id/query', query.runQuery)
  .get('/datasources/:id/query-history', query.queryHistory)
  .delete('/datasources/:id/query-history', query.clearQueryHistory)
  .post('/datasources/:id/query/export', query.exportQuery)
  .get('/datasources/activity/insights', dataActivity.dataActivityInsights)
  .get('/saved-queries', savedQueries.listSavedQueries)
  .get('/saved-queries/insights', savedQueries.savedQueryInsights)
  .get('/saved-queries/:id', savedQueries.getSavedQuery)
  .post('/saved-queries', savedQueries.createSavedQuery)
  .patch('/saved-queries/:id', savedQueries.updateSavedQuery)
  .delete('/saved-queries/:id', savedQueries.deleteSavedQuery)
  .get('/datasources/:id/explorer/structure', explorer.tableStructure)
  .get('/datasources/:id/explorer/columns', explorer.tableColumns)
  .get('/datasources/:id/explorer/rows', explorer.tableRows)
  .get('/datasources/:id/explorer/facets', explorer.tableFacets)
  .post('/datasources/:id/explorer/exports', explorer.startTableExport)
  .get('/explorer-exports/:id', explorer.getTableExport)
  .post('/explorer-exports/:id/link', explorer.tableExportLink)
  .get('/datasource-exports/:token', explorer.downloadTableExport)
  .post('/datasources/:id/explorer/rows', explorer.insertRow)
  .patch('/datasources/:id/explorer/rows', explorer.updateRow)
  .delete('/datasources/:id/explorer/rows', explorer.deleteRow)
  .get('/forms/:id/storage', destinations.formStorage)
  .get('/destinations', destinations.listDestinations)
  .get('/destinations/insights', destinations.destinationInsights)
  .post('/destinations', destinations.createDestination)
  .get('/destinations/:id', destinations.getDestination)
  .patch('/destinations/:id', destinations.patchDestination)
  .delete('/destinations/:id', destinations.removeDestination)
  .post('/destinations/:id/columns', destinations.addColumns)
  .get('/destinations/:id/deliveries', destinations.listDeliveries)
  .post('/destinations/:id/retry', destinations.retryDeliveries)
  .post('/destinations/:id/backfill', destinations.startBackfill)
  .delete('/datasources/:id', dataSources.deleteDataSource)
  .get('/field-library', library.listSavedFields)
  .post('/field-library', library.saveField)
  .delete('/field-library/:id', library.deleteSavedField)
  .get('/option-lists', library.listOptionLists)
  .post('/option-lists', library.createOptionList)
  .patch('/option-lists/:id', library.updateOptionList)
  .delete('/option-lists/:id', library.deleteOptionList)
  .get('/themes', themes.listThemes)
  .get('/themes/insights', themes.themeInsights)
  .get('/page-designs', pageDesigns.listPageDesigns)
  .get('/page-designs/insights', pageDesigns.pageDesignInsights)
  .get('/page-designs/:id', pageDesigns.getPageDesign)
  .get('/themes/:id', themes.getTheme)
  .get('/directory', getDirectory)
  // Public form pages (F10), no sign-in.
  .get('/public/forms/:key', publicForms.getPublicForm)
  .post('/public/forms/:key/submit', publicForms.submitPublicForm)
  .post('/public/forms/:key/verify', publicForms.sendVerification)
  .post('/public/forms/:key/sessions', publicForms.startDraft)
  .put('/public/forms/:key/sessions/:token', publicForms.saveDraft)
  .get('/public/forms/:key/sessions/:token', publicForms.getDraft)
  .post('/public/forms/:key/verify/confirm', publicForms.confirmVerification)
  .post('/public/forms/:key/uploads', publicForms.requestUpload)
  .post('/public/forms/:key/challenge', publicForms.issueChallenge)
  .post('/public/forms/:key/unlock', publicForms.unlockForm)
  .get('/public/short/:code', publicForms.getShortLink)
  .post('/public/forms/:key/uploads/:id/complete', publicForms.completeUpload)
  .get('/templates', templates.listTemplates)
  .get('/templates/facets', templates.templateFacets)
  .get('/templates/insights', templates.templateInsights)
  .get('/templates/categories', templates.listTemplateCategories)
  .post('/templates/translate-content', templates.translateFormContent)
  .post('/templates', templates.createTemplate)
  .get('/templates/:key', templates.getTemplate)
  .patch('/templates/:key', templates.updateTemplate)
  .post('/templates/:key/duplicate', templates.duplicateTemplate)
  .post('/templates/:key/sync', templates.syncTemplate)
  .delete('/templates/:key', templates.deleteTemplate)
  .post('/themes', themes.createTheme)
  .patch('/themes/:id', themes.updateTheme)
  .post('/themes/:id/duplicate', themes.duplicateTheme)
  .delete('/themes/:id', themes.deleteTheme)
  .post('/page-designs', pageDesigns.createPageDesign)
  .patch('/page-designs/:id', pageDesigns.updatePageDesign)
  .post('/page-designs/:id/duplicate', pageDesigns.duplicatePageDesign)
  .delete('/page-designs/:id', pageDesigns.deletePageDesign)
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

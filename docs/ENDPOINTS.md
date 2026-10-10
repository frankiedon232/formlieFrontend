# Endpoints checklist (generated from the frontend mock, 2026-10-10)

Every endpoint the finished frontend calls, taken from the mock router (`C:/UNETPROJECTS/formalieFrontend/server/mock/index.ts`). The mock answers exactly the shapes in `API-CONTRACT.md`. When a detail isn't in the contract, the mock file named here is the reference: read it, never change it. Tick an endpoint when the real backend answers it with the same shape, checks the same permissions, writes the same audit actions, and has tests, including cross-tenant ones. The frontend switches off the mock once every box is ticked.

Per file: **Guards** are the checks the mock makes (`requireAuth` signed in, `requireAdmin` admin only, `requireAction` / `requireLevel` / `requireResponses` per-form access, `requireOwned` / `requireResource` scope on an item, `requireFeature` / `requireFormSlot` / `requireDatabase` plan limits, `requireAi` AI allowance). **Permissions** are codes from `shared/utils/auth/permissions.ts` used in that file. **Audit** lists actions from `shared/utils/audit/events.ts` that the file records.

Total: 399 endpoints in the portal API, plus the public API service and the server-rendered form routes at the end.

## `routes/system.ts`

- [ ] `GET /api/v1/health` (`health`)
- [ ] `POST /api/v1/crypto/handshake` (`handshake`)
- [ ] `GET /api/v1/auth/csrf` (`csrf`)

## `routes/tenants.ts`

- [ ] `GET /api/v1/tenants/public` (`publicProfile`)
- [ ] `GET /api/v1/tenants/subdomain-availability` (`subdomainAvailability`)
- [ ] `POST /api/v1/tenants/find-workspace` (`findWorkspace`)
- [ ] `POST /api/v1/tenants/find-workspace/verify` (`findWorkspaceVerify`)

## `routes/auth.ts`

- **Guards:** `requireAuth`, `requireTenant`
- **Audit:** `auth.login.blocked`, `auth.login.failed`, `auth.login.succeeded`, `auth.logout`, `auth.otp.failed`, `auth.otp.locked`, `auth.otp.sent`, `auth.password.reset`, `auth.password.reset_requested`, `workspace.created`

- [ ] `POST /api/v1/auth/login` (`login`)
- [ ] `POST /api/v1/auth/otp/verify` (`verifyOtp`)
- [ ] `POST /api/v1/auth/otp/resend` (`resendOtp`)
- [ ] `POST /api/v1/auth/refresh` (`refresh`)
- [ ] `POST /api/v1/auth/logout` (`logout`)
- [ ] `POST /api/v1/auth/signup` (`signup`)
- [ ] `POST /api/v1/auth/signup/complete` (`signupComplete`)
- [ ] `POST /api/v1/auth/exchange-ticket` (`exchangeTicket`)
- [ ] `POST /api/v1/auth/password/forgot` (`forgotPassword`)
- [ ] `POST /api/v1/auth/password/reset` (`resetPassword`)
- [ ] `GET /api/v1/auth/oauth/{provider}/start` (`oauthStart`)
- [ ] `GET /api/v1/me` (`me`)

## `routes/sso.ts`

- **Guards:** `requireAdmin`, `requireFeature`
- **Audit:** `settings.updated`

- [ ] `GET /api/v1/auth/sso/start` (`ssoStart`)
- [ ] `GET /api/v1/settings/sso` (`getSso`)
- [ ] `PUT /api/v1/settings/sso` (`saveSso`)
- [ ] `POST /api/v1/settings/sso/test` (`testSso`)
- [ ] `POST /api/v1/settings/sso/status` (`setSsoStatus`)
- [ ] `DELETE /api/v1/settings/sso` (`removeSso`)

## `routes/forms.ts`

- **Guards:** `requireAction`, `requireAuth`, `requireFormSlot`
- **Audit:** `forms.archived`, `forms.closed`, `forms.created`, `forms.deleted`, `forms.folder_access_changed`, `forms.folder_created`, `forms.folder_deleted`, `forms.folder_renamed`, `forms.purged`, `forms.reopened`, `forms.restored`, `forms.unarchived`, `forms.unpublished`, `forms.updated`

- [ ] `GET /api/v1/forms` (`listForms`)
- [ ] `POST /api/v1/forms` (`createForm`)
- [ ] `GET /api/v1/forms/facets` (`formFacets`)
- [ ] `POST /api/v1/forms/import` (`importForm`)
- [ ] `POST /api/v1/forms/bulk` (`bulkForms`)
- [ ] `DELETE /api/v1/forms/trash` (`emptyTrash`)
- [ ] `GET /api/v1/forms/{id}` (`getForm`)
- [ ] `PATCH /api/v1/forms/{id}` (`patchForm`)
- [ ] `DELETE /api/v1/forms/{id}` (`deleteForm`)
- [ ] `POST /api/v1/forms/{id}/duplicate` (`duplicateForm`)
- [ ] `POST /api/v1/forms/{id}/{action}` (`formLifecycle`)
- [ ] `GET /api/v1/folders` (`listFolders`)
- [ ] `POST /api/v1/folders` (`createFolder`)
- [ ] `PATCH /api/v1/folders/{id}` (`renameFolder`)
- [ ] `DELETE /api/v1/folders/{id}` (`deleteFolder`)
- [ ] `PUT /api/v1/folders/{id}/access` (`setFolderAccess`)

## `routes/formInvites.ts`

- **Guards:** `requireAction`, `requireAuth`
- **Audit:** `forms.shared`

- [ ] `POST /api/v1/forms/pass` (`formPass`)
- [ ] `GET /api/v1/forms/{id}/invites` (`listInvites`)
- [ ] `POST /api/v1/forms/{id}/invites` (`createInvites`)
- [ ] `POST /api/v1/forms/{id}/invites/{inviteId}/resend` (`resendInvite`)
- [ ] `DELETE /api/v1/forms/{id}/invites/{inviteId}` (`revokeInvite`)

## `routes/formOverview.ts`

- **Guards:** `requireAuth`, `requireLevel`

- [ ] `GET /api/v1/forms/{id}/overview` (`getFormOverview`)

## `routes/formShare.ts`

- **Guards:** `requireAction`, `requireAuth`
- **Permissions:** `forms.view`
- **Audit:** `forms.shared`

- [ ] `GET /api/v1/forms/{id}/share` (`getShare`)
- [ ] `PUT /api/v1/forms/{id}/share` (`saveShare`)
- [ ] `GET /api/v1/forms/{id}/share/link-check` (`checkLink`)
- [ ] `POST /api/v1/forms/{id}/short-link` (`createShortLink`)
- [ ] `DELETE /api/v1/forms/{id}/short-link` (`removeShortLink`)

## `routes/formAccess.ts`

- **Guards:** `requireAction`, `requireAuth`
- **Permissions:** `forms.view`

- [ ] `GET /api/v1/forms/{id}/access` (`formAccess`)

## `routes/formDraft.ts`

- **Guards:** `requireAction`, `requireAuth`
- **Audit:** `forms.published`, `forms.updated`

- [ ] `GET /api/v1/forms/{id}/builder` (`getBuilder`)
- [ ] `GET /api/v1/forms/{id}/preview` (`previewForm`)
- [ ] `PUT /api/v1/forms/{id}/draft` (`saveDraft`)
- [ ] `POST /api/v1/forms/{id}/publish` (`publishForm`)
- [ ] `POST /api/v1/forms/{id}/discard` (`discardDraft`)
- [ ] `GET /api/v1/forms/{id}/versions` (`listVersions`)
- [ ] `GET /api/v1/forms/{id}/versions/{vid}` (`getVersion`)
- [ ] `POST /api/v1/forms/{id}/versions/{vid}/restore` (`restoreVersion`)

## `routes/responses.ts`

- **Guards:** `requireAuth`, `requireResponses`
- **Audit:** `responses.deleted`, `responses.updated`

- [ ] `GET /api/v1/forms/{id}/responses` (`listFormResponses`)
- [ ] `GET /api/v1/forms/{id}/responses/insights` (`formInsights`)
- [ ] `GET /api/v1/forms/{id}/responses/tags` (`formResponseTags`)
- [ ] `GET /api/v1/responses/insights` (`inboxInsights`)
- [ ] `GET /api/v1/responses/forms` (`listResponseForms`)
- [ ] `POST /api/v1/responses/bulk` (`bulkResponses`)
- [ ] `GET /api/v1/responses` (`listResponses`)
- [ ] `GET /api/v1/responses/{id}` (`getResponse`)
- [ ] `PATCH /api/v1/responses/{id}` (`patchResponse`)
- [ ] `DELETE /api/v1/responses/{id}` (`deleteResponse`)
- [ ] `POST /api/v1/responses/{id}/notes` (`addNote`)

## `routes/analytics.ts`

- **Guards:** `requireAuth`, `requireLevel`

- [ ] `GET /api/v1/analytics/overview` (`analyticsOverview`)
- [ ] `GET /api/v1/analytics/forms` (`analyticsForms`)
- [ ] `GET /api/v1/analytics/forms/{id}/funnel` (`formFunnel`)

## `routes/apiService.ts`

- **Guards:** `requireAdmin`, `requireOwned`
- **Permissions:** `api.service_delete`, `api.service_edit`
- **Audit:** `api.endpoint_created`, `api.endpoint_deleted`, `api.endpoint_disabled`, `api.endpoint_enabled`, `api.endpoint_updated`, `api.key_rotated`, `api.service_created`, `api.service_deleted`, `api.service_disabled`, `api.service_enabled`, `api.service_updated`, `api.token_created`, `api.token_deleted`, `api.token_revealed`, `api.token_revoked`, `api.token_rotated`, `api.token_updated`

- [ ] `GET /api/v1/api-service/settings` (`apiSettings`)
- [ ] `GET /api/v1/api-service/setup` (`apiSetup`)
- [ ] `POST /api/v1/api-service/key/rotate` (`rotateApiKey`)
- [ ] `GET /api/v1/api-tokens` (`listApiTokens`)
- [ ] `GET /api/v1/api-tokens/insights` (`apiTokenInsights`)
- [ ] `POST /api/v1/api-tokens` (`createApiToken`)
- [ ] `GET /api/v1/api-tokens/{id}` (`getApiToken`)
- [ ] `PATCH /api/v1/api-tokens/{id}` (`updateApiToken`)
- [ ] `DELETE /api/v1/api-tokens/{id}` (`deleteApiToken`)
- [ ] `POST /api/v1/api-tokens/{id}/rotate` (`rotateApiToken`)
- [ ] `POST /api/v1/api-tokens/{id}/revoke` (`revokeApiToken`)
- [ ] `POST /api/v1/api-tokens/{id}/reveal` (`revealApiToken`)
- [ ] `GET /api/v1/api-services` (`listApiServices`)
- [ ] `GET /api/v1/api-services/insights` (`apiServiceInsights`)
- [ ] `POST /api/v1/api-services` (`createApiService`)
- [ ] `GET /api/v1/api-services/{id}` (`getApiService`)
- [ ] `PATCH /api/v1/api-services/{id}` (`updateApiService`)
- [ ] `DELETE /api/v1/api-services/{id}` (`deleteApiService`)
- [ ] `POST /api/v1/api-services/{id}/duplicate` (`duplicateApiService`)
- [ ] `GET /api/v1/api-endpoints` (`listApiEndpoints`)
- [ ] `GET /api/v1/api-endpoints/insights` (`apiEndpointInsights`)
- [ ] `GET /api/v1/api-endpoints/form-fields` (`apiEndpointFormFields`)
- [ ] `POST /api/v1/api-endpoints` (`createApiEndpoint`)
- [ ] `GET /api/v1/api-endpoints/{id}` (`getApiEndpoint`)
- [ ] `PATCH /api/v1/api-endpoints/{id}` (`updateApiEndpoint`)
- [ ] `DELETE /api/v1/api-endpoints/{id}` (`deleteApiEndpoint`)

## `routes/apiConnections.ts`

- **Guards:** `requireAdmin`

- [ ] `GET /api/v1/api-service/connections` (`apiConnections`)

## `routes/apiAccess.ts`

- **Guards:** `requireAdmin`
- **Audit:** `api.limits_changed`, `api.rule_created`, `api.rule_deleted`, `api.rule_disabled`, `api.rule_enabled`, `api.rule_updated`

- [ ] `GET /api/v1/api-service/limits` (`getRateLimits`)
- [ ] `PUT /api/v1/api-service/limits` (`updateRateLimits`)
- [ ] `GET /api/v1/api-access-rules` (`listAccessRules`)
- [ ] `GET /api/v1/api-access-rules/insights` (`accessInsights`)
- [ ] `POST /api/v1/api-access-rules` (`createAccessRule`)
- [ ] `POST /api/v1/api-access-rules/test` (`testAccess`)
- [ ] `GET /api/v1/api-access-rules/{id}` (`getAccessRule`)
- [ ] `PATCH /api/v1/api-access-rules/{id}` (`updateAccessRule`)
- [ ] `DELETE /api/v1/api-access-rules/{id}` (`deleteAccessRule`)

## `routes/apiTraffic.ts`

- **Guards:** `requireAdmin`
- **Audit:** `api.logging_changed`

- [ ] `GET /api/v1/api-logs` (`listApiLogs`)
- [ ] `GET /api/v1/api-logs/insights` (`apiLogInsights`)
- [ ] `GET /api/v1/api-logs/settings` (`getApiLogSettings`)
- [ ] `PUT /api/v1/api-logs/settings` (`updateApiLogSettings`)
- [ ] `GET /api/v1/api-logs/{id}` (`getApiLog`)
- [ ] `GET /api/v1/api-analytics` (`apiAnalytics`)

## `routes/apiDocs.ts`

- **Guards:** `requireAdmin`

- [ ] `POST /api/v1/api-endpoints/{id}/try` (`tryEndpoint`)

## `routes/webhooks.ts`

- **Guards:** `requireAdmin`
- **Audit:** `api.token_created`, `integrations.webhook_created`, `integrations.webhook_deleted`, `integrations.webhook_disabled`, `integrations.webhook_enabled`, `integrations.webhook_resent`, `integrations.webhook_updated`

- [ ] `GET /api/v1/webhooks` (`listWebhooks`)
- [ ] `GET /api/v1/webhooks/insights` (`webhookInsights`)
- [ ] `POST /api/v1/webhooks` (`createWebhook`)
- [ ] `GET /api/v1/webhooks/{id}` (`getWebhook`)
- [ ] `PATCH /api/v1/webhooks/{id}` (`updateWebhook`)
- [ ] `DELETE /api/v1/webhooks/{id}` (`deleteWebhook`)
- [ ] `POST /api/v1/webhooks/{id}/test` (`testWebhook`)
- [ ] `GET /api/v1/webhook-deliveries` (`listDeliveries`)
- [ ] `GET /api/v1/webhook-deliveries/{id}` (`getDelivery`)
- [ ] `POST /api/v1/webhook-deliveries/{id}/resend` (`resendDelivery`)

## `routes/responseExports.ts`

- **Guards:** `requireAuth`
- **Audit:** `responses.export_deleted`, `responses.export_downloaded`, `responses.exported`

- [ ] `POST /api/v1/forms/{id}/responses/export` (`exportFormResponses`)
- [ ] `GET /api/v1/responses/exports` (`listResponseExports`)
- [ ] `GET /api/v1/responses/exports/{id}` (`getResponseExport`)
- [ ] `POST /api/v1/responses/exports/{id}/link` (`responseExportLink`)
- [ ] `DELETE /api/v1/responses/exports/{id}` (`deleteResponseExport`)
- [ ] `GET /api/v1/response-exports/{token}` (`downloadResponseExport`)

## `routes/responseFiles.ts`

- **Guards:** `requireAuth`

- [ ] `POST /api/v1/responses/{id}/files` (`fileLink`)
- [ ] `GET /api/v1/response-files/{token}` (`serveResponseFile`)

## `routes/folders.ts`

- **Guards:** `requireAuth`

- [ ] `GET /api/v1/folders/overview` (`folderOverview`)
- [ ] `GET /api/v1/folders/{id}` (`getFolder`)

## `routes/dataSources.ts`

- **Guards:** `requireAdmin`, `requireDatabase`, `requireOwned`
- **Audit:** `data.connection_created`, `data.connection_deleted`, `data.connection_disabled`, `data.connection_duplicated`, `data.connection_enabled`, `data.connection_tested`, `data.connection_updated`, `data.credentials_changed`

- [ ] `GET /api/v1/datasources` (`listDataSources`)
- [ ] `GET /api/v1/datasources/insights` (`dataSourceInsights`)
- [ ] `GET /api/v1/datasources/meta` (`dataSourceMeta`)
- [ ] `POST /api/v1/datasources/test` (`startConnectionTest`)
- [ ] `GET /api/v1/datasources/tests/{id}` (`getConnectionTest`)
- [ ] `POST /api/v1/datasources` (`createDataSource`)
- [ ] `GET /api/v1/datasources/{id}` (`getDataSource`)
- [ ] `PATCH /api/v1/datasources/{id}` (`patchDataSource`)
- [ ] `POST /api/v1/datasources/{id}/test` (`testSavedConnection`)
- [ ] `POST /api/v1/datasources/{id}/duplicate` (`duplicateDataSource`)
- [ ] `DELETE /api/v1/datasources/{id}` (`deleteDataSource`)

## `routes/destinations.ts`

- **Guards:** `requireAdmin`, `requireAuth`
- **Audit:** `data.backfill_started`, `data.column_added`, `data.deliveries_retried`, `data.destination_created`, `data.destination_paused`, `data.destination_removed`, `data.destination_resumed`, `data.destination_updated`, `data.table_created`

- [ ] `GET /api/v1/datasources/{id}/tables` (`listTables`)
- [ ] `GET /api/v1/forms/{id}/storage` (`formStorage`)
- [ ] `GET /api/v1/destinations` (`listDestinations`)
- [ ] `GET /api/v1/destinations/insights` (`destinationInsights`)
- [ ] `POST /api/v1/destinations` (`createDestination`)
- [ ] `GET /api/v1/destinations/{id}` (`getDestination`)
- [ ] `PATCH /api/v1/destinations/{id}` (`patchDestination`)
- [ ] `DELETE /api/v1/destinations/{id}` (`removeDestination`)
- [ ] `POST /api/v1/destinations/{id}/columns` (`addColumns`)
- [ ] `GET /api/v1/destinations/{id}/deliveries` (`listDeliveries`)
- [ ] `POST /api/v1/destinations/{id}/retry` (`retryDeliveries`)
- [ ] `POST /api/v1/destinations/{id}/backfill` (`startBackfill`)

## `routes/explorer.ts`

- **Guards:** `requireAdmin`
- **Audit:** `data.row_deleted`, `data.row_inserted`, `data.row_updated`, `data.table_exported`

- [ ] `GET /api/v1/datasources/{id}/explorer/tables` (`explorerTables`)
- [ ] `GET /api/v1/datasources/{id}/explorer/structure` (`tableStructure`)
- [ ] `GET /api/v1/datasources/{id}/explorer/columns` (`tableColumns`)
- [ ] `GET /api/v1/datasources/{id}/explorer/rows` (`tableRows`)
- [ ] `GET /api/v1/datasources/{id}/explorer/facets` (`tableFacets`)
- [ ] `POST /api/v1/datasources/{id}/explorer/exports` (`startTableExport`)
- [ ] `GET /api/v1/explorer-exports/{id}` (`getTableExport`)
- [ ] `POST /api/v1/explorer-exports/{id}/link` (`tableExportLink`)
- [ ] `GET /api/v1/datasource-exports/{token}` (`downloadTableExport`)
- [ ] `POST /api/v1/datasources/{id}/explorer/rows` (`insertRow`)
- [ ] `PATCH /api/v1/datasources/{id}/explorer/rows` (`updateRow`)
- [ ] `DELETE /api/v1/datasources/{id}/explorer/rows` (`deleteRow`)

## `routes/explorerSchema.ts`

- **Guards:** `requireAdmin`
- **Audit:** `data.table_altered`, `data.table_dropped`, `data.table_truncated`, `data.user_table_created`

- [ ] `POST /api/v1/datasources/{id}/explorer/tables` (`createTable`)
- [ ] `POST /api/v1/datasources/{id}/explorer/changes` (`changeTable`)

## `routes/query.ts`

- **Guards:** `requireAdmin`
- **Audit:** `data.query_exported`, `data.query_run`

- [ ] `POST /api/v1/datasources/{id}/query` (`runQuery`)
- [ ] `GET /api/v1/datasources/{id}/query-history` (`queryHistory`)
- [ ] `DELETE /api/v1/datasources/{id}/query-history` (`clearQueryHistory`)
- [ ] `POST /api/v1/datasources/{id}/query/export` (`exportQuery`)

## `routes/dataActivity.ts`

- **Guards:** `requireAdmin`

- [ ] `GET /api/v1/datasources/activity/insights` (`dataActivityInsights`)

## `routes/help.ts`

- **Guards:** `requireAuth`

- [ ] `GET /api/v1/help/home` (`helpHome`)
- [ ] `GET /api/v1/help/articles` (`listHelpArticles`)
- [ ] `GET /api/v1/help/articles/{id}` (`getHelpArticle`)
- [ ] `POST /api/v1/help/articles/{id}/feedback` (`helpFeedback`)
- [ ] `GET /api/v1/help/search` (`searchHelp`)
- [ ] `GET /api/v1/help/faqs` (`listHelpFaqs`)
- [ ] `GET /api/v1/help/glossary` (`listHelpGlossary`)
- [ ] `GET /api/v1/help/context` (`helpContext`)
- [ ] `GET /api/v1/help/tours` (`helpTours`)

## `routes/ai.ts`

- **Guards:** `requireAuth`
- **Audit:** `ai.disabled`, `ai.enabled`, `ai.request_deleted`, `ai.settings_updated`

- [ ] `GET /api/v1/ai/settings` (`getAiSettings`)
- [ ] `PATCH /api/v1/ai/settings` (`updateAiSettings`)
- [ ] `GET /api/v1/ai/usage` (`getAiUsage`)
- [ ] `GET /api/v1/ai/requests` (`listAiRequests`)
- [ ] `GET /api/v1/ai/requests/insights` (`aiRequestInsights`)
- [ ] `GET /api/v1/ai/requests/{id}` (`getAiRequest`)
- [ ] `DELETE /api/v1/ai/requests/{id}` (`deleteAiRequest`)

## `routes/aiCreate.ts`

- **Guards:** `requireAction`, `requireAi`, `requireAuth`
- **Permissions:** `forms.create`, `forms.save_template`
- **Audit:** `ai.applied`, `forms.updated`

- [ ] `POST /api/v1/ai/requests/{id}/apply` (`applyAiRequest`)
- [ ] `POST /api/v1/ai/requests/{id}/discard` (`discardAiRequest`)
- [ ] `POST /api/v1/ai/forms/draft` (`draftFormRoute`)
- [ ] `POST /api/v1/ai/templates/draft` (`draftTemplateRoute`)
- [ ] `POST /api/v1/ai/themes/draft` (`draftThemeRoute`)

## `routes/aiAssist.ts`

- **Guards:** `requireAction`, `requireAi`, `requireAuth`

- [ ] `POST /api/v1/ai/forms/{id}/assist` (`assistFormRoute`)

## `routes/aiWrite.ts`

- **Guards:** `requireAction`, `requireAi`, `requireAuth`

- [ ] `POST /api/v1/ai/forms/{id}/translate` (`translateFormRoute`)
- [ ] `POST /api/v1/ai/forms/{id}/rewrite` (`rewriteFormRoute`)

## `routes/aiAnalyse.ts`

- **Guards:** `requireAi`, `requireAuth`

- [ ] `POST /api/v1/ai/analysis` (`analysisRoute`)
- [ ] `POST /api/v1/ai/digest` (`digestRoute`)
- [ ] `POST /api/v1/ai/ask` (`askRoute`)
- [ ] `POST /api/v1/ai/responses/{id}/summary` (`responseSummaryRoute`)

## `routes/savedQueries.ts`

- **Guards:** `requireAdmin`
- **Audit:** `data.saved_query_deleted`, `data.saved_query_saved`

- [ ] `GET /api/v1/saved-queries` (`listSavedQueries`)
- [ ] `GET /api/v1/saved-queries/insights` (`savedQueryInsights`)
- [ ] `GET /api/v1/saved-queries/{id}` (`getSavedQuery`)
- [ ] `POST /api/v1/saved-queries` (`createSavedQuery`)
- [ ] `PATCH /api/v1/saved-queries/{id}` (`updateSavedQuery`)
- [ ] `DELETE /api/v1/saved-queries/{id}` (`deleteSavedQuery`)

## `routes/library.ts`

- **Guards:** `requireAuth`, `requireResource`
- **Audit:** `forms.field_removed`, `forms.field_saved`

- [ ] `GET /api/v1/field-library` (`listSavedFields`)
- [ ] `POST /api/v1/field-library` (`saveField`)
- [ ] `DELETE /api/v1/field-library/{id}` (`deleteSavedField`)

## `routes/people.ts`

- **Guards:** `requireAdmin`
- **Audit:** `auth.login.succeeded`

- [ ] `GET /api/v1/people` (`listPeople`)
- [ ] `GET /api/v1/people/insights` (`peopleInsights`)
- [ ] `GET /api/v1/people/{id}` (`getPerson`)

## `routes/invites.ts`

- **Guards:** `requireAdmin`
- **Audit:** `users.approved`, `users.invite_link`, `users.invite_resent`, `users.invite_revoked`, `users.invited`, `users.joined`, `users.profile_created`, `users.rejected`, `users.requested`, `users.signup_link_changed`

- [ ] `GET /api/v1/people/signup-link` (`getSignupLink`)
- [ ] `POST /api/v1/people` (`createProfile`)
- [ ] `PUT /api/v1/people/signup-link` (`updateSignupLink`)
- [ ] `POST /api/v1/people/signup-link/new` (`renewSignupLink`)
- [ ] `POST /api/v1/people/{id}/approve` (`approvePerson`)
- [ ] `POST /api/v1/people/{id}/reject` (`rejectPerson`)
- [ ] `POST /api/v1/people/invites` (`invitePeople`)
- [ ] `POST /api/v1/people/{id}/invite/resend` (`resendInvite`)
- [ ] `POST /api/v1/people/{id}/invite/link` (`inviteLink`)
- [ ] `DELETE /api/v1/people/{id}/invite` (`revokeInvite`)
- [ ] `GET /api/v1/public/invites/{token}` (`previewInvite`)
- [ ] `POST /api/v1/public/invites/{token}/accept` (`acceptInvite`)

## `routes/me.ts`

- **Guards:** `requireAuth`
- **Audit:** `auth.password.changed`, `auth.recovery_codes.created`, `auth.session.revoked`, `auth.two_step.disabled`, `auth.two_step.enabled`, `users.profile_updated`

- [ ] `GET /api/v1/me/profile` (`getProfile`)
- [ ] `GET /api/v1/me/tours` (`myTours`)
- [ ] `PATCH /api/v1/me/tours` (`updateMyTours`)
- [ ] `PATCH /api/v1/me/profile` (`updateProfile`)
- [ ] `POST /api/v1/me/password` (`changePassword`)
- [ ] `POST /api/v1/me/two-step/app` (`startApp`)
- [ ] `POST /api/v1/me/two-step/app/confirm` (`confirmApp`)
- [ ] `POST /api/v1/me/two-step/app/remove` (`removeApp`)
- [ ] `POST /api/v1/me/two-step/recovery` (`newRecovery`)
- [ ] `POST /api/v1/me/two-step/phone` (`startPhone`)
- [ ] `POST /api/v1/me/two-step/phone/confirm` (`confirmPhone`)
- [ ] `DELETE /api/v1/me/two-step/phone` (`removePhone`)
- [ ] `GET /api/v1/me/sessions` (`mySessions`)
- [ ] `DELETE /api/v1/me/sessions/{id}` (`endMySession`)
- [ ] `POST /api/v1/me/sessions/sign-out-others` (`endOtherSessions`)

## `routes/roles.ts`

- **Guards:** `requireAdmin`
- **Audit:** `users.role_created`, `users.role_deleted`, `users.role_updated`

- [ ] `GET /api/v1/roles` (`listRoles`)
- [ ] `GET /api/v1/roles/insights` (`rolesInsights`)
- [ ] `POST /api/v1/roles` (`createRole`)
- [ ] `GET /api/v1/roles/{id}` (`getRole`)
- [ ] `PATCH /api/v1/roles/{id}` (`updateRole`)
- [ ] `POST /api/v1/roles/{id}/duplicate` (`duplicateRole`)
- [ ] `DELETE /api/v1/roles/{id}` (`deleteRole`)

## `routes/peopleManage.ts`

- **Guards:** `requireAdmin`
- **Audit:** `users.disabled`, `users.enabled`, `users.password_requested`, `users.role_changed`, `users.signed_out`, `users.two_step_reset`, `users.updated`

- [ ] `POST /api/v1/people/bulk` (`bulkPeople`)
- [ ] `PATCH /api/v1/people/{id}` (`updatePerson`)
- [ ] `POST /api/v1/people/{id}/disable` (`disablePerson`)
- [ ] `POST /api/v1/people/{id}/enable` (`enablePerson`)
- [ ] `POST /api/v1/people/{id}/sign-out` (`signOutPerson`)
- [ ] `POST /api/v1/people/{id}/password` (`requestPassword`)
- [ ] `POST /api/v1/people/{id}/two-step/reset` (`resetTwoStep`)

## `routes/optionLists.ts`

- **Guards:** `requireAuth`, `requireResource`
- **Audit:** `forms.list_created`, `forms.list_deleted`, `forms.list_synced`, `forms.list_updated`

- [ ] `GET /api/v1/option-lists` (`listOptionLists`)
- [ ] `GET /api/v1/option-lists/insights` (`optionListInsights`)
- [ ] `POST /api/v1/option-lists` (`createOptionList`)
- [ ] `GET /api/v1/option-lists/{id}` (`getOptionList`)
- [ ] `PATCH /api/v1/option-lists/{id}` (`updateOptionList`)
- [ ] `DELETE /api/v1/option-lists/{id}` (`deleteOptionList`)
- [ ] `GET /api/v1/option-lists/{id}/usage` (`optionListUsage`)
- [ ] `GET /api/v1/option-lists/{id}/options` (`lookupListOptions`)
- [ ] `POST /api/v1/option-lists/{id}/sync` (`syncOptionList`)
- [ ] `POST /api/v1/option-lists/{id}/duplicate` (`duplicateOptionList`)

## `routes/themes.ts`

- **Guards:** `requireAuth`, `requireResource`
- **Audit:** `forms.theme_created`, `forms.theme_deleted`, `forms.theme_updated`

- [ ] `GET /api/v1/themes` (`listThemes`)
- [ ] `GET /api/v1/themes/insights` (`themeInsights`)
- [ ] `GET /api/v1/themes/{id}` (`getTheme`)
- [ ] `POST /api/v1/themes` (`createTheme`)
- [ ] `PATCH /api/v1/themes/{id}` (`updateTheme`)
- [ ] `POST /api/v1/themes/{id}/duplicate` (`duplicateTheme`)
- [ ] `DELETE /api/v1/themes/{id}` (`deleteTheme`)

## `routes/pageDesigns.ts`

- **Guards:** `requireAuth`, `requireResource`
- **Audit:** `forms.page_design_created`, `forms.page_design_deleted`, `forms.page_design_updated`

- [ ] `GET /api/v1/page-designs` (`listPageDesigns`)
- [ ] `GET /api/v1/page-designs/insights` (`pageDesignInsights`)
- [ ] `GET /api/v1/page-designs/{id}` (`getPageDesign`)
- [ ] `POST /api/v1/page-designs` (`createPageDesign`)
- [ ] `PATCH /api/v1/page-designs/{id}` (`updatePageDesign`)
- [ ] `POST /api/v1/page-designs/{id}/duplicate` (`duplicatePageDesign`)
- [ ] `DELETE /api/v1/page-designs/{id}` (`deletePageDesign`)

## `routes/directory.ts`

- **Guards:** `requireAuth`

- [ ] `GET /api/v1/directory` (`getDirectory`)

## `routes/publicForms.ts`

- **Audit:** `responses.submitted`

- [ ] `GET /api/v1/public/forms/{key}` (`getPublicForm`)
- [ ] `GET /api/v1/public/forms/{key}/options` (`lookupOptions`)
- [ ] `POST /api/v1/public/forms/{key}/submit` (`submitPublicForm`)
- [ ] `POST /api/v1/public/forms/{key}/verify` (`sendVerification`)
- [ ] `POST /api/v1/public/forms/{key}/sessions` (`startDraft`)
- [ ] `PUT /api/v1/public/forms/{key}/sessions/{token}` (`saveDraft`)
- [ ] `GET /api/v1/public/forms/{key}/sessions/{token}` (`getDraft`)
- [ ] `POST /api/v1/public/forms/{key}/verify/confirm` (`confirmVerification`)
- [ ] `POST /api/v1/public/forms/{key}/uploads` (`requestUpload`)
- [ ] `POST /api/v1/public/forms/{key}/challenge` (`issueChallenge`)
- [ ] `POST /api/v1/public/forms/{key}/unlock` (`unlockForm`)
- [ ] `GET /api/v1/public/short/{code}` (`getShortLink`)
- [ ] `POST /api/v1/public/forms/{key}/uploads/{id}/complete` (`completeUpload`)

## `routes/templates.ts`

- **Guards:** `requireAction`, `requireAuth`, `requireResource`
- **Audit:** `forms.template_created`, `forms.template_deleted`, `forms.template_duplicated`, `forms.template_updated`

- [ ] `GET /api/v1/templates` (`listTemplates`)
- [ ] `GET /api/v1/templates/facets` (`templateFacets`)
- [ ] `GET /api/v1/templates/insights` (`templateInsights`)
- [ ] `GET /api/v1/templates/categories` (`listTemplateCategories`)
- [ ] `POST /api/v1/templates/translate-content` (`translateFormContent`)
- [ ] `POST /api/v1/templates` (`createTemplate`)
- [ ] `GET /api/v1/templates/{key}` (`getTemplate`)
- [ ] `PATCH /api/v1/templates/{key}` (`updateTemplate`)
- [ ] `POST /api/v1/templates/{key}/duplicate` (`duplicateTemplate`)
- [ ] `POST /api/v1/templates/{key}/sync` (`syncTemplate`)
- [ ] `DELETE /api/v1/templates/{key}` (`deleteTemplate`)

## `routes/navigation.ts`

- **Guards:** `requireAuth`
- **Permissions:** `people.view`

- [ ] `GET /api/v1/navigation/counts` (`navigationCounts`)

## `routes/notifications.ts`

- **Guards:** `requireAdmin`, `requireAuth`

- [ ] `GET /api/v1/notifications` (`getFeed`)
- [ ] `POST /api/v1/notifications/read` (`readNotifications`)
- [ ] `DELETE /api/v1/notifications/read` (`clearNotifications`)
- [ ] `POST /api/v1/notifications/digest/send` (`sendDigest`)

## `routes/org.ts`

- **Guards:** `requireAdmin`
- **Audit:** `settings.org_archived`, `settings.org_created`, `settings.org_deleted`, `settings.org_imported`, `settings.org_merged`, `settings.org_restored`, `settings.org_updated`

- [ ] `GET /api/v1/org/{kind}` (`listOrg`)
- [ ] `GET /api/v1/org/{kind}/insights` (`orgInsights`)
- [ ] `POST /api/v1/org/{kind}` (`createOrgItem`)
- [ ] `POST /api/v1/org/{kind}/merge` (`mergeOrgItems`)
- [ ] `POST /api/v1/org/{kind}/import` (`importOrgItems`)
- [ ] `GET /api/v1/org/{kind}/{id}` (`getOrgItem`)
- [ ] `GET /api/v1/org/{kind}/{id}/usage` (`orgUsage`)
- [ ] `PATCH /api/v1/org/{kind}/{id}` (`updateOrgItem`)
- [ ] `POST /api/v1/org/{kind}/{id}/archive` (`archiveOrgItem`)
- [ ] `POST /api/v1/org/{kind}/{id}/restore` (`restoreOrgItem`)
- [ ] `DELETE /api/v1/org/{kind}/{id}` (`deleteOrgItem`)

## `routes/settings.ts`

- **Guards:** `requireAdmin`, `requireAuth`, `requireFeature`
- **Audit:** `auth.login.blocked`, `auth.login.failed`, `auth.login.succeeded`, `auth.otp.failed`, `auth.otp.locked`, `auth.session.revoked`, `settings.updated`

- [ ] `GET /api/v1/settings` (`getSettings`)
- [ ] `GET /api/v1/settings/localisation` (`getLocalisation`)
- [ ] `PATCH /api/v1/settings/localisation` (`patchSection`)
- [ ] `GET /api/v1/settings/security` (`getSection`)
- [ ] `GET /api/v1/settings/appearance` (`getAppearance`)
- [ ] `PATCH /api/v1/settings/appearance` (`patchSection`)
- [ ] `GET /api/v1/settings/privacy` (`getSection`)
- [ ] `PATCH /api/v1/settings/privacy` (`patchSection`)
- [ ] `GET /api/v1/settings/form_defaults` (`getFormDefaults`)
- [ ] `PATCH /api/v1/settings/form_defaults` (`patchSection`)
- [ ] `GET /api/v1/settings/emails` (`getSection`)
- [ ] `PATCH /api/v1/settings/emails` (`patchSection`)
- [ ] `GET /api/v1/settings/notifications` (`getSection`)
- [ ] `PATCH /api/v1/settings/notifications` (`patchSection`)
- [ ] `PATCH /api/v1/settings/security` (`patchSection`)
- [ ] `GET /api/v1/settings/security/sessions` (`listSessions`)
- [ ] `POST /api/v1/settings/security/sessions/sign-out` (`signOutSessions`)
- [ ] `GET /api/v1/settings/security/activity` (`securityActivity`)
- [ ] `GET /api/v1/settings/{section}` (`getSection`)
- [ ] `PATCH /api/v1/settings/{section}` (`patchSection`)

## `routes/emails.ts`

- **Guards:** `requireAdmin`

- [ ] `GET /api/v1/settings/emails/templates/{key}` (`getTemplate`)
- [ ] `POST /api/v1/settings/emails/preview` (`previewEmail`)
- [ ] `POST /api/v1/settings/emails/test` (`testEmail`)
- [ ] `GET /api/v1/settings/emails/sent` (`listSent`)
- [ ] `GET /api/v1/settings/emails/sent/{id}` (`getSent`)

## `routes/emailSending.ts`

- **Guards:** `requireAdmin`, `requireFeature`
- **Audit:** `settings.updated`

- [ ] `GET /api/v1/settings/emails/sending` (`getSending`)
- [ ] `PUT /api/v1/settings/emails/sending/domain` (`addSendingDomain`)
- [ ] `POST /api/v1/settings/emails/sending/domain/check` (`checkSendingDomain`)
- [ ] `DELETE /api/v1/settings/emails/sending/domain` (`removeSendingDomain`)
- [ ] `PUT /api/v1/settings/emails/sending/smtp` (`saveSmtp`)
- [ ] `POST /api/v1/settings/emails/sending/smtp/test` (`testSmtp`)
- [ ] `DELETE /api/v1/settings/emails/sending/smtp` (`removeSmtp`)
- [ ] `POST /api/v1/settings/emails/sending/mode` (`setSendingMode`)

## `routes/dashboard.ts`

- **Guards:** `requireAuth`
- **Permissions:** `api.view`

- [ ] `GET /api/v1/dashboard` (`workspaceDashboard`)

## `routes/dashboardForms.ts`

- **Guards:** `requireAuth`

- [ ] `GET /api/v1/dashboard/forms` (`formsDashboard`)

## `routes/dashboardData.ts`

- **Guards:** `requireAuth`

- [ ] `GET /api/v1/dashboard/data` (`dataDashboard`)

## `routes/dashboardApi.ts`

- **Guards:** `requireAuth`
- **Permissions:** `api.view`

- [ ] `GET /api/v1/dashboard/api` (`apiDashboard`)

## `routes/billing.ts`

- **Guards:** `requireAuth`
- **Audit:** `settings.updated`

- [ ] `GET /api/v1/billing` (`getBilling`)
- [ ] `GET /api/v1/billing/plans` (`getPlans`)
- [ ] `GET /api/v1/billing/invoices` (`getInvoices`)
- [ ] `POST /api/v1/billing/preview` (`previewChange`)
- [ ] `POST /api/v1/billing/change` (`changePlan`)
- [ ] `POST /api/v1/billing/cancel` (`cancelPlan`)
- [ ] `POST /api/v1/billing/resume` (`resumePlan`)
- [ ] `DELETE /api/v1/billing/scheduled` (`dropScheduled`)
- [ ] `PATCH /api/v1/billing/settings` (`patchBillingSettings`)
- [ ] `DELETE /api/v1/billing/payment-method` (`removePaymentMethod`)

## `routes/billingCheckout.ts`

- **Guards:** `requireAuth`
- **Audit:** `settings.updated`

- [ ] `POST /api/v1/billing/checkout` (`startCheckout`)
- [ ] `POST /api/v1/billing/checkout/{id}/complete` (`completeCheckout`)

## `billing/webhook.ts`

- **Audit:** `settings.updated`

- [ ] `POST /api/v1/billing/webhooks/payoneer` (`payoneerWebhook`)

## `routes/address.ts`

- **Guards:** `requireAdmin`, `requireFeature`
- **Audit:** `settings.updated`

- [ ] `GET /api/v1/settings/address` (`getAddress`)
- [ ] `POST /api/v1/settings/address/subdomain` (`changeWorkspaceSubdomain`)
- [ ] `PUT /api/v1/settings/address/domain` (`addDomain`)
- [ ] `POST /api/v1/settings/address/domain/check` (`checkDomain`)
- [ ] `DELETE /api/v1/settings/address/domain` (`removeDomain`)

## `routes/dataRegion.ts`

- **Guards:** `requireAuth`

- [ ] `GET /api/v1/settings/data-region` (`getDataRegion`)

## `routes/dataPrivacy.ts`

- **Guards:** `requireAdmin`
- **Audit:** `settings.data_deleted`, `settings.data_exported`

- [ ] `GET /api/v1/settings/privacy/retention-preview` (`retentionPreview`)
- [ ] `POST /api/v1/privacy/requests/search` (`searchRequest`)
- [ ] `POST /api/v1/privacy/requests/export` (`exportRequest`)
- [ ] `POST /api/v1/privacy/requests/delete` (`deleteRequest`)

## `routes/onboarding.ts`

- **Guards:** `requireAdmin`
- **Audit:** `settings.updated`, `users.invited`, `workspace.setup_completed`, `workspace.updated`

- [ ] `GET /api/v1/onboarding` (`getOnboarding`)
- [ ] `PATCH /api/v1/onboarding` (`patchOnboarding`)
- [ ] `POST /api/v1/onboarding/finish` (`finishOnboarding`)

## `routes/uploads.ts`

- **Guards:** `requireAdmin`, `requireAuth`

- [ ] `POST /api/v1/uploads` (`createUpload`)
- [ ] `POST /api/v1/uploads/{id}/complete` (`completeUpload`)
- [ ] `PUT /api/v1/storage/{token}` (`storeUpload`)
- [ ] `GET /api/v1/files/{id}` (`serveFile`)

## `routes/audit.ts`

- **Guards:** `requireAdmin`
- **Audit:** `audit.exported`

- [ ] `GET /api/v1/audit-logs` (`listAuditLogs`)
- [ ] `GET /api/v1/audit-logs/facets` (`auditFacets`)
- [ ] `POST /api/v1/audit-logs/export` (`exportAuditLogs`)
- [ ] `GET /api/v1/audit-logs/{id}` (`getAuditLog`)
- [ ] `GET /api/v1/exports/{id}` (`getExportJob`)
- [ ] `GET /api/v1/downloads/{token}` (`download`)

## Public API service (`publicApi.ts`, host `api.formalie.dev`, no envelope, SECURITY-PROTOCOL §9)

- **Audit:** `responses.deleted`, `responses.submitted`, `responses.updated`

- [ ] `POST /{apiKey}/token` client id + secret to a short-lived access token
- [ ] `GET /{apiKey}/{endpoint}` list (page, per_page, sort, filters)
- [ ] `GET /{apiKey}/{endpoint}/{recordId}` one record
- [ ] `POST /{apiKey}/{endpoint}` new response (`Formalie-Key` idempotent replays)
- [ ] `PUT /{apiKey}/{endpoint}/{recordId}` change accepted answers
- [ ] `DELETE /{apiKey}/{endpoint}/{recordId}` remove (kept in the audit trail)
- [ ] `POST /{apiKey}/{endpoint}/files?field=` one file (multipart)
- [ ] `OPTIONS` preflight: 204 with CORS headers for allowed websites, else `FRM-API-1015`

Order of checks (keep it): address key, endpoint, access rules (IP, Origin domain, country), rate limit per IP, token, rate limits per token and endpoint, switched on, method, scope, required headers, signature, the form's rules.

## Server-rendered public pages (internal, service to service)

- [ ] Internal published-form fetch for `/{formKey}/fill` and `/{formKey}/embed` (`server/routes/_ssr/public-forms/[key].get.ts`), only with the server-only internal token header `x-formalie-internal`
- [ ] Internal short-link resolve for `/s/{code}` (`server/routes/_ssr/short/[code].get.ts`)

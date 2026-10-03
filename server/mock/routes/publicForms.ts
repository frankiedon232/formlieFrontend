/**
 * Public form endpoints (docs/API-CONTRACT.md → Public, F10) — no sign-in. The workspace comes from
 * the host (`{sub}.formalie.dev`) or, on `forms.formalie.dev`, from the form key. Requests are
 * enveloped like every other call (anonymous handshake + pre-session CSRF).
 *
 *   GET  /public/forms/:key          the published form, its state, SEO and workspace branding
 *   POST /public/forms/:key/submit   one response per fill-in session (Idempotency-Key)
 */
import { z } from 'zod'
import type { PublicForm, PublicFormState, PublicSubmitResult } from '#shared/types/public'
import { checkSubmission } from '#shared/utils/forms/submission'
import type { FormSchemaV1 } from '#shared/utils/forms/schema'
import { resolveTheme } from '#shared/utils/forms/theme'
import { APP_LOCALES } from '#shared/utils/i18n/locales'
import { tenantOf } from '../core/auth'
import { recordAudit } from '../core/audit'
import { MockError, ok } from '../core/respond'
import { defineMockRoute } from '../core/route'
import { parseBody } from '../core/validate'
import { findByPublicKey, formsOf, saveForms, type StoredForm } from '../data/formStore'
import { responseForSubmission, responsesOf, saveResponses } from '../data/responseStore'
import { MOCK_TENANTS, type MockTenant } from '../data/tenants'
import { ensureSchema } from './formDraft'
import { websiteOf } from './onboarding'

const RESPONDENT = { type: 'user' as const, id: null, name: 'Respondent', email: null }

/** The form behind a public key on this host (a workspace host only serves its own forms). */
function locate(event: Parameters<typeof tenantOf>[0], key: string): { tenant: MockTenant; form: StoredForm } {
  const { context, tenant } = tenantOf(event)
  const found =
    context.kind === 'tenant'
      ? tenant && tenant.status !== 'suspended'
        ? findByPublicKey([tenant], key)
        : null
      : findByPublicKey(MOCK_TENANTS.filter(item => item.status !== 'suspended'), key)
  if (!found) throw new MockError('FRM-FORM-1001')
  return found
}

function stateOf(form: StoredForm): PublicFormState {
  if (form.status === 'published') return 'open'
  if (form.status === 'closed' || form.status === 'archived') return 'closed'
  return 'not_published'
}

/** What respondents fill in: the published version (seeded sample forms get theirs on first open). */
function publishedSchema(tenant: MockTenant, form: StoredForm): FormSchemaV1 | null {
  if (!form.published_schema && form.status !== 'draft') ensureSchema(form, tenant)
  return form.published_schema ?? null
}

const branding = (tenant: MockTenant) => ({ logo_url: tenant.logo_url ?? null, primary: tenant.brand_color ?? null })
const offered = (schema: FormSchemaV1 | null) => {
  const main = schema?.settings?.language ?? 'en'
  return APP_LOCALES.some(locale => locale.code === main) ? main : 'en'
}

/** Plain text from the first paragraph block, for the link-card description. */
function summaryText(schema: FormSchemaV1 | null): string {
  const intro = schema?.pages.flatMap(page => page.rows.flatMap(row => row.fields)).find(field => field.type === 'paragraph')
  const html = String((intro?.props as { html?: string } | undefined)?.html ?? '')
  return html.replace(/<[^>]+>/g, ' ').replace(/\s+/g, ' ').trim().slice(0, 200)
}

/** The published form for respondents (also used by the server-rendered page, server/routes/_ssr). */
export function publicFormView(event: Parameters<typeof tenantOf>[0], key: string): PublicForm {
  const { tenant, form } = locate(event, key)
  const state = stateOf(form)
  const published = state === 'open' ? publishedSchema(tenant, form) : null
  const schema = published ? { ...structuredClone(published), theme: resolveTheme(published.theme, branding(tenant)) as unknown as Record<string, unknown> } : null
  const language = offered(published)
  return {
    key: form.public_key,
    name: form.name,
    state: schema ? state : state === 'open' ? 'not_published' : state,
    schema,
    workspace: { name: tenant.name, logo_url: tenant.logo_url ?? null, primary: tenant.brand_color ?? null, subdomain: tenant.subdomain ?? null, website: websiteOf(tenant) },
    seo: {
      title: form.name,
      description: summaryText(published) || String((published?.theme as { header?: { subtitle?: string } } | undefined)?.header?.subtitle ?? ''),
      image: null,
      noindex: state !== 'open',
    },
    languages: [language],
    language,
  }
}

/** GET /public/forms/:key — the published form for respondents. */
export const getPublicForm = defineMockRoute(({ event }) => ok<PublicForm>(publicFormView(event, getRouterParam(event, 'key') ?? '')))

const submitBody = z.object({
  data: z.record(z.string(), z.unknown()),
  channel: z.enum(['link', 'embed']).default('link'),
  language: z.string().max(10).optional(),
})
const SUBMISSION_ID = /^[A-Za-z0-9-]{16,64}$/

/** POST /public/forms/:key/submit — store the response once per fill-in session. */
export const submitPublicForm = defineMockRoute(({ event, body }) => {
  const key = getRouterParam(event, 'key') ?? ''
  const submissionId = getHeader(event, 'idempotency-key') ?? ''
  if (!SUBMISSION_ID.test(submissionId))
    throw new MockError('FRM-GEN-1002', [{ field: 'Idempotency-Key', message: 'Send the fill-in session id as Idempotency-Key.' }])
  const input = parseBody(submitBody, body)
  const { tenant, form } = locate(event, key)

  const schema = stateOf(form) === 'open' ? publishedSchema(tenant, form) : null
  if (!schema) throw new MockError(stateOf(form) === 'closed' ? 'FRM-FORM-1002' : 'FRM-FORM-1001')
  const thankYou = {
    title: schema.thank_you?.title ?? '',
    message: schema.thank_you?.message ?? '',
    redirect_url: schema.thank_you?.redirect_url ?? null,
  }

  // The same session again (double click, retry, back button): the response it already made.
  const earlier = responseForSubmission(tenant, form.id, submissionId)
  if (earlier) return ok<PublicSubmitResult>({ response_id: earlier.id, duplicate: true, thank_you: thankYou })

  const { issues, answers } = checkSubmission(schema, input.data)
  if (issues.length) throw new MockError('FRM-RESP-1001', issues.map(issue => ({ field: issue.key, message: issue.code })))

  const response = {
    id: crypto.randomUUID(),
    form_id: form.id,
    form_version: form.versions?.[0]?.number ?? null,
    submitted_at: new Date().toISOString(),
    language: input.language ?? offered(schema),
    data: answers,
    submission_id: submissionId,
    channel: input.channel,
    meta: { ip: getRequestIP(event, { xForwardedFor: true }) ?? 'unknown', user_agent: (getHeader(event, 'user-agent') ?? '').slice(0, 300) },
  }
  responsesOf(tenant).responses.unshift(response)
  saveResponses()
  const stored = formsOf(tenant).forms.find(item => item.id === form.id)
  if (stored) {
    stored.responses_count += 1
    saveForms()
  }
  recordAudit(event, tenant, {
    action: 'responses.submitted',
    actor: RESPONDENT,
    resource: { type: 'form', id: form.id, name: form.name },
    changes: [{ field: 'channel', before: null, after: input.channel }],
  })
  return ok<PublicSubmitResult>({ response_id: response.id, duplicate: false, thank_you: thankYou }, {}, 201)
})

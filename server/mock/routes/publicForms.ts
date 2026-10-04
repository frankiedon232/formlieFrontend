/**
 * Public form endpoints (docs/API-CONTRACT.md → Public, F10) — no sign-in. The workspace comes from
 * the host (`{sub}.formalie.dev`) or, on `forms.formalie.dev`, from the form key. Requests are
 * enveloped like every other call (anonymous handshake + pre-session CSRF).
 *
 *   GET  /public/forms/:key          the published form, its state, SEO and workspace branding
 *   POST /public/forms/:key/submit   one response per fill-in session (Idempotency-Key)
 *   POST /public/forms/:key/uploads  a pre-signed link for one file of a file question (+ /:id/complete)
 */
import { createHash, createHmac, randomBytes, timingSafeEqual } from 'node:crypto'
import { z } from 'zod'
import { availabilityOf } from '#shared/utils/forms/availability'
import { identityOf, maskEmail, matchIdentity, normaliseEmail } from '#shared/utils/forms/identity'
import type { FileAnswer, PublicForm, PublicFormState, PublicSubmitResult } from '#shared/types/public'
import { checkSubmission } from '#shared/utils/forms/submission'
import type { FormSchemaV1 } from '#shared/utils/forms/schema'
import { resolveTheme } from '#shared/utils/forms/theme'
import { APP_LOCALES } from '#shared/utils/i18n/locales'
import { tenantOf } from '../core/auth'
import { recordAudit } from '../core/audit'
import { MockError, ok } from '../core/respond'
import { defineMockRoute } from '../core/route'
import { parseBody } from '../core/validate'
import { findByPublicKey, findByShortCode, formsOf, saveForms, type StoredForm } from '../data/formStore'
import { formLink, publicHosts, SHORT_CODE_PATTERN } from '#shared/utils/urls/public'
import { frameAncestors } from '#shared/utils/urls/embed-domains'
import { responseForSubmission, responsesOf, saveResponses } from '../data/responseStore'
import { MOCK_TENANTS, type MockTenant } from '../data/tenants'
import { ensureSchema } from './formDraft'
import { websiteOf } from './onboarding'
import { draftOf, newResumeToken, putDraft, RESUME_TTL_DAYS } from '../data/resumeStore'
import { attachRespondentFiles, completedUploadUrl, completeRespondentUpload, createRespondentTicket, respondentFile } from './uploads'
import { seoOf } from '../data/formSeo'
import { allFields, isLocked } from '#shared/utils/forms/build'
import { acceptsFile, parseAccept } from '#shared/utils/forms/file-types'
import { fileAnswers, isFileField, maxFileBytes } from '#shared/utils/forms/file-answers'
import { checkWork } from '#shared/utils/forms/proof-of-work'
import type { UploadTicket } from '#shared/types/onboarding'
import { platformLegal } from '../data/platformStore'
import { hashPassword } from './formShare'

const RESPONDENT = { type: 'user' as const, id: null, name: 'Respondent', email: null }

/** This browser's device id (a random cookie, set on the first submission; not personal data). */
const DEVICE_COOKIE = 'formalie_device'
function deviceOf(event: Parameters<typeof tenantOf>[0]): string {
  const existing = getCookie(event, DEVICE_COOKIE)
  if (existing && /^[A-Za-z0-9-]{20,64}$/.test(existing)) return existing
  const fresh = crypto.randomUUID()
  // SameSite=None: embedded forms run inside other websites; the cookie is only a random id.
  setCookie(event, DEVICE_COOKIE, fresh, { httpOnly: true, secure: true, sameSite: 'none', path: '/', maxAge: 60 * 60 * 24 * 365 })
  return fresh
}
/** The answers in a stable order, hashed: the same response twice has the same fingerprint. */
function fingerprintOf(answers: Record<string, unknown>): string {
  const stable = Object.keys(answers)
    .sort()
    .map(key => [key, typeof answers[key] === 'string' ? (answers[key] as string).trim().toLowerCase() : answers[key]])
  return createHash('sha256').update(JSON.stringify(stable)).digest('hex')
}

/** The form behind a public key on this host (a workspace host only serves its own forms). */
function locate(event: Parameters<typeof tenantOf>[0], key: string): { tenant: MockTenant; form: StoredForm } {
  const { context, tenant } = tenantOf(event)
  const found =
    context.kind === 'tenant'
      ? tenant && tenant.status !== 'suspended'
        ? findByPublicKey([tenant], key)
        : null
      : findByPublicKey(MOCK_TENANTS.filter(item => item.status !== 'suspended'), key, { sharedHost: true })
  if (!found) throw new MockError('FRM-FORM-1001')
  return found
}

/** The form's response limit is used up (Share settings, F10 M3). */
const limitReached = (form: StoredForm) => form.response_limit != null && form.responses_count >= form.response_limit

function stateOf(form: StoredForm, { ignoreLimit = false } = {}): PublicFormState {
  if (form.status === 'published') {
    const window = availabilityOf(form)
    if (window === 'expired' || window === 'scheduled') return window
    return !ignoreLimit && limitReached(form) ? 'limit_reached' : 'open'
  }
  if (form.status === 'closed' || form.status === 'archived') return 'closed'
  return 'not_published'
}

// ── Password access (F10 M3) ───────────────────────────────────────────────────────────
// After the right password the browser gets an HttpOnly cookie for this form (12 hours), signed
// with the password's version: changing the password locks everyone out again.
const UNLOCK_SECRET = randomBytes(32)
const UNLOCK_TTL_MS = 12 * 3_600_000
const unlockCookie = (form: StoredForm) => `formalie_unlock_${form.public_key}`
const unlockSignature = (form: StoredForm, until: number) =>
  createHmac('sha256', UNLOCK_SECRET).update(`${form.id}|${form.password?.version ?? 0}|${until}`).digest('base64url')

function unlocked(event: Parameters<typeof tenantOf>[0], form: StoredForm): boolean {
  if ((form.access ?? 'public') !== 'password') return true
  const [until, signature] = (getCookie(event, unlockCookie(form)) ?? '').split('.')
  if (!until || !signature || Number(until) < Date.now()) return false
  const expected = Buffer.from(unlockSignature(form, Number(until)))
  const given = Buffer.from(signature)
  return expected.length === given.length && timingSafeEqual(expected, given)
}

/** The form takes responses from this visitor right now: open, unlocked (password) — or the reason why not. */
function takingResponses(event: Parameters<typeof tenantOf>[0], key: string, { ignoreLimit = false } = {}) {
  const { tenant, form } = locate(event, key)
  const state = stateOf(form, { ignoreLimit })
  const schema = state === 'open' ? publishedSchema(tenant, form) : null
  if (!schema)
    throw new MockError(
      state === 'closed'
        ? 'FRM-FORM-1002'
        : state === 'expired'
          ? 'FRM-FORM-1015'
          : state === 'scheduled'
            ? 'FRM-FORM-1016'
            : state === 'limit_reached'
              ? 'FRM-FORM-1003'
              : 'FRM-FORM-1001',
    )
  if (!unlocked(event, form)) throw new MockError('FRM-FORM-1005')
  return { tenant, form, schema }
}

const unlockBody = z.object({ password: z.string().min(1).max(100) })
const unlockAttempts = new Map<string, number[]>()

/** POST /public/forms/:key/unlock — the form's password → an unlock cookie for this browser. */
export const unlockForm = defineMockRoute(({ event, body }) => {
  const { form } = locate(event, getRouterParam(event, 'key') ?? '')
  if ((form.access ?? 'public') !== 'password' || !form.password) return ok({ unlocked: true })
  // At most 10 tries per 10 minutes from one address for one form.
  const who = `${form.id}:${getRequestIP(event, { xForwardedFor: true }) ?? 'unknown'}`
  const recent = (unlockAttempts.get(who) ?? []).filter(at => at > Date.now() - 600_000)
  if (recent.length >= 10) throw new MockError('FRM-GEN-1029')
  unlockAttempts.set(who, [...recent, Date.now()])
  const given = Buffer.from(hashPassword(parseBody(unlockBody, body).password, form.password.salt))
  const stored = Buffer.from(form.password.hash)
  if (given.length !== stored.length || !timingSafeEqual(given, stored)) throw new MockError('FRM-FORM-1017')
  unlockAttempts.delete(who)
  const until = Date.now() + UNLOCK_TTL_MS
  // SameSite=None: password forms work inside embeds too.
  setCookie(event, unlockCookie(form), `${until}.${unlockSignature(form, until)}`, { httpOnly: true, secure: true, sameSite: 'none', path: '/', maxAge: UNLOCK_TTL_MS / 1000 })
  return ok({ unlocked: true })
})

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

/** The published form for respondents (also used by the server-rendered page, server/routes/_ssr). */
export function publicFormView(event: Parameters<typeof tenantOf>[0], key: string): PublicForm {
  const { tenant, form } = locate(event, key)
  const state = stateOf(form)
  const locked = state === 'open' && !unlocked(event, form)
  const published = state === 'open' ? publishedSchema(tenant, form) : null
  const schema = published ? { ...structuredClone(published), theme: resolveTheme(published.theme, branding(tenant)) as unknown as Record<string, unknown> } : null
  // The form's language also for full, closed, expired, scheduled and locked pages (no questions are sent then).
  const language = offered(published ?? form.published_schema ?? form.schema)
  const seo = seoOf(form)
  // Link cards need a full address for the image (link previews fetch it from outside).
  const imagePath = seo.imageUploadId ? completedUploadUrl(seo.imageUploadId, tenant.id) : null
  const seoImage = imagePath ? `https://${getRequestHost(event, { xForwardedHost: true })}${imagePath}` : null
  return {
    key: form.custom_link || form.public_key,
    name: form.name,
    state: schema ? state : state === 'open' ? 'not_published' : state,
    opens_at: form.opens_at ?? null,
    closes_at: form.closes_at ?? null,
    schema: locked ? null : schema,
    workspace: { name: tenant.name, logo_url: tenant.logo_url ?? null, primary: tenant.brand_color ?? null, subdomain: tenant.subdomain ?? null, website: websiteOf(tenant) },
    // Search & link preview (decision 95): the creator's text and image, else from the form.
    seo: {
      title: seo.title,
      description: seo.description,
      image: seoImage,
      noindex: state !== 'open' || seo.noindex,
    },
    legal: platformLegal(event),
    languages: [language],
    language,
    locked,
    embed_ancestors: frameAncestors(form.embed_domains ?? [], useRuntimeConfig(event).public.rootDomain),
  }
}

/** GET /public/forms/:key — the published form for respondents. */
export const getPublicForm = defineMockRoute(({ event }) => ok<PublicForm>(publicFormView(event, getRouterParam(event, 'key') ?? '')))

const submitBody = z.object({
  data: z.record(z.string(), z.unknown()),
  channel: z.enum(['link', 'embed']).default('link'),
  language: z.string().max(10).optional(),
  /** The respondent confirmed this response is for another person (same browser, F10). */
  for_someone_else: z.boolean().optional(),
  /** The respondent confirmed they are not the person of a similar earlier response. */
  confirmed_different: z.boolean().optional(),
  /** From /verify/confirm when the form verifies the respondent's email. */
  verification_token: z.string().max(80).optional(),
  /** Save and resume: the draft this response finishes (closed on success). */
  resume_token: z.string().max(80).optional(),
  /** Spam check (decision 89): the solved challenge from POST /challenge. */
  challenge: z.object({ token: z.string().max(300), nonce: z.number().int().min(0) }).optional(),
  /** A field people never see; bots fill it in. */
  trap: z.string().max(500).optional(),
})
const SUBMISSION_ID = /^[A-Za-z0-9-]{16,64}$/

/** POST /public/forms/:key/submit — store the response once per fill-in session. */
export const submitPublicForm = defineMockRoute(async ({ event, body }) => {
  const key = getRouterParam(event, 'key') ?? ''
  const submissionId = getHeader(event, 'idempotency-key') ?? ''
  if (!SUBMISSION_ID.test(submissionId))
    throw new MockError('FRM-GEN-1002', [{ field: 'Idempotency-Key', message: 'Send the fill-in session id as Idempotency-Key.' }])
  const input = parseBody(submitBody, body)
  const { tenant, form, schema } = takingResponses(event, key, { ignoreLimit: true })
  const thankYou = {
    title: schema.thank_you?.title ?? '',
    message: schema.thank_you?.message ?? '',
    redirect_url: schema.thank_you?.redirect_url ?? null,
  }

  // The same session again (double click, retry, back button): the response it already made.
  const earlier = responseForSubmission(tenant, form.id, submissionId)
  if (earlier) return ok<PublicSubmitResult>({ response_id: earlier.id, duplicate: true, thank_you: thankYou })
  if (limitReached(form)) throw new MockError('FRM-FORM-1003')

  // Spam (decision 89): a filled-in trap looks accepted but stores nothing; too many from one
  // address → slow down; without a solved challenge (or sent within seconds of opening) → refused.
  if (input.trap?.trim()) return ok<PublicSubmitResult>({ response_id: crypto.randomUUID(), duplicate: false, thank_you: thankYou }, {}, 201)
  const sender = `${form.id}:${getRequestIP(event, { xForwardedFor: true }) ?? 'unknown'}`
  const sent = (submitsBy.get(sender) ?? []).filter(at => at > Date.now() - 600_000)
  if (sent.length >= SUBMITS_PER_10_MIN) throw new MockError('FRM-GEN-1029')
  submitsBy.set(sender, [...sent, Date.now()])
  const salt = await provenHuman(form.public_key, input.challenge)
  if (!salt) throw new MockError('FRM-RESP-1009')

  const { issues, answers } = checkSubmission(schema, input.data)
  // Files: each must be a finished upload for this form and question (names and sizes come from storage).
  const fileIds: string[] = []
  for (const field of allFields(schema).filter(item => isFileField(item.type) && item.key in answers)) {
    const value = answers[field.key]
    if (value == null || (Array.isArray(value) && !value.length)) continue
    const files = fileAnswers(value).map(file => respondentFile(file.id, form.id, field.key))
    if (!Array.isArray(value) || files.length !== value.length || files.some(file => !file)) issues.push({ key: field.key, code: 'file' })
    else {
      answers[field.key] = files
      fileIds.push(...files.map(file => file!.id))
    }
  }
  if (issues.length) throw new MockError('FRM-RESP-1001', issues.map(issue => ({ field: issue.key, message: issue.code })))

  // Telling people apart (owner, 2026-10-03; shared/utils/forms/identity.ts). With the respondent's
  // own email: same → refused, a typo away → asked + flagged. Without: one per browser.
  // The exact same answers are never accepted twice.
  const deviceId = deviceOf(event)
  const earlierResponses = responsesOf(tenant).responses.filter(item => item.form_id === form.id)
  const identity = identityOf(schema)
  if (identity.verify && identity.email) {
    const email = normaliseEmail(answers[identity.email])
    // Nothing to send a code to: the email is required when the form verifies it.
    if (!email) throw new MockError('FRM-RESP-1001', [{ field: identity.email, message: 'required' }])
    if (!useVerification(form.id, email, input.verification_token))
      throw new MockError('FRM-RESP-1008', [{ field: identity.email, message: maskEmail(answers[identity.email]) }])
  }
  let possibleDuplicate: { of: string; reason: string } | undefined
  if (identity.email) {
    const match = matchIdentity(schema, answers, earlierResponses, identity)
    const key = identity.email
    const hint = JSON.stringify({ at: match.record?.submitted_at, email: maskEmail(match.record?.data[key]) })
    if (match.level === 'clear') throw new MockError('FRM-RESP-1006', [{ field: key, message: hint }])
    if (match.level === 'likely') {
      if (!input.confirmed_different) throw new MockError('FRM-RESP-1007', [{ field: key, message: hint }])
      possibleDuplicate = { of: match.record!.id, reason: match.reason! }
    }
  } else if (!input.for_someone_else && earlierResponses.some(item => item.device_id === deviceId)) throw new MockError('FRM-RESP-1004')
  const fingerprint = fingerprintOf(answers)
  if (earlierResponses.some(item => item.fingerprint === fingerprint)) throw new MockError('FRM-RESP-1005')

  const response = {
    id: crypto.randomUUID(),
    form_id: form.id,
    form_version: form.versions?.[0]?.number ?? null,
    submitted_at: new Date().toISOString(),
    language: input.language ?? offered(schema),
    data: answers,
    submission_id: submissionId,
    device_id: deviceId,
    fingerprint,
    ...(possibleDuplicate ? { possible_duplicate: possibleDuplicate } : {}),
    channel: input.channel,
    meta: { ip: getRequestIP(event, { xForwardedFor: true }) ?? 'unknown', user_agent: (getHeader(event, 'user-agent') ?? '').slice(0, 300) },
  }
  responsesOf(tenant).responses.unshift(response)
  saveResponses()
  usedChallenges.set(salt, Date.now() + CHALLENGE_TTL_MS)
  attachRespondentFiles(fileIds, response.id)
  if (input.resume_token) {
    const draft = draftOf(input.resume_token, form.id)
    if (draft) putDraft(input.resume_token, { ...draft, closed: true, data: {}, updated_at: new Date().toISOString() })
  }
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

// ── Verify the respondent's email (optional per form) ───────────────────────────────────
interface Verification {
  formId: string
  email: string
  code: string
  expiresAt: number
  attempts: number
  token?: string
  tokenExpiresAt?: number
}
const verifications = new Map<string, Verification>()
const sentAt = new Map<string, number[]>()
const VERIFY_TTL = 10 * 60_000
const TOKEN_TTL = 30 * 60_000
const slot = (formId: string, email: string) => `${formId}:${email}`

/** A confirmed email for this form (the token from /verify/confirm), used once. */
function useVerification(formId: string, email: string, token: string | undefined): boolean {
  const entry = verifications.get(slot(formId, email))
  if (!entry?.token || !token || entry.token !== token || (entry.tokenExpiresAt ?? 0) < Date.now()) return false
  verifications.delete(slot(formId, email))
  return true
}

const verifyBody = z.object({ email: z.email().max(200) })
/** POST /public/forms/:key/verify — send a 6-digit code to the respondent's email. */
export const sendVerification = defineMockRoute(({ event, body }) => {
  const { form } = takingResponses(event, getRouterParam(event, 'key') ?? '')
  const email = normaliseEmail(parseBody(verifyBody, body).email)
  if (!email) throw new MockError('FRM-GEN-1002', [{ field: 'email', message: 'Enter a valid email.' }])
  // At most 5 codes an hour for one email on one form.
  const recent = (sentAt.get(slot(form.id, email)) ?? []).filter(at => at > Date.now() - 3_600_000)
  if (recent.length >= 5) throw new MockError('FRM-AUTH-1004')
  sentAt.set(slot(form.id, email), [...recent, Date.now()])
  const code = String(Math.floor(100000 + Math.random() * 900000))
  verifications.set(slot(form.id, email), { formId: form.id, email, code, expiresAt: Date.now() + VERIFY_TTL, attempts: 0 })
  // A real backend emails the code; the mock hands it to the dev screen only.
  return ok({ sent_to: maskEmail(email), expires_in: VERIFY_TTL / 1000 }, import.meta.dev ? { dev_code: code } : {})
})

const confirmBody = z.object({ email: z.email().max(200), code: z.string().regex(/^\d{6}$/) })
/** POST /public/forms/:key/verify/confirm — the code → a short-lived token for the submission. */
export const confirmVerification = defineMockRoute(({ event, body }) => {
  const { form } = takingResponses(event, getRouterParam(event, 'key') ?? '')
  const input = parseBody(confirmBody, body)
  const email = normaliseEmail(input.email) ?? ''
  const entry = verifications.get(slot(form.id, email))
  if (!entry || entry.expiresAt < Date.now()) throw new MockError('FRM-AUTH-1003')
  if (entry.attempts >= 5) throw new MockError('FRM-AUTH-1004')
  if (entry.code !== input.code) {
    entry.attempts += 1
    throw new MockError('FRM-AUTH-1003')
  }
  entry.token = crypto.randomUUID()
  entry.tokenExpiresAt = Date.now() + TOKEN_TTL
  return ok({ token: entry.token })
})

// ── Save and resume (F10 M2) ────────────────────────────────────────────────────────────
const draftBody = z.object({
  data: z.record(z.string(), z.unknown()),
  page: z.number().int().min(0).max(500).default(0),
  /** Send the resume link to this address ("Save and continue later"). */
  email: z.email().max(200).optional(),
})

/** The form must take responses and have Save and resume on. */
function resumable(event: Parameters<typeof tenantOf>[0]) {
  const { tenant, form, schema } = takingResponses(event, getRouterParam(event, 'key') ?? '')
  if (!schema.settings?.save_resume) throw new MockError('FRM-PERM-1001')
  return { tenant, form }
}
/** The resume link — sent by email (a real backend); the mock returns it to the dev screen. */
const resumeLink = (event: Parameters<typeof tenantOf>[0], key: string, token: string) =>
  `https://${getRequestHost(event, { xForwardedHost: true })}/${key}/fill?resume=${encodeURIComponent(token)}`

/** POST /public/forms/:key/sessions — start a draft → its resume token. */
export const startDraft = defineMockRoute(({ event, body }) => {
  const { tenant, form } = resumable(event)
  const input = parseBody(draftBody, body)
  const now = new Date()
  const token = newResumeToken()
  putDraft(token, {
    tenantId: tenant.id,
    formId: form.id,
    data: input.data,
    page: input.page,
    email: input.email ?? null,
    created_at: now.toISOString(),
    updated_at: now.toISOString(),
    expires_at: new Date(now.getTime() + RESUME_TTL_DAYS * 86_400_000).toISOString(),
    closed: false,
  })
  const meta = import.meta.dev && input.email ? { dev_resume_url: resumeLink(event, form.public_key, token) } : {}
  return ok({ resume_token: token, expires_at: new Date(now.getTime() + RESUME_TTL_DAYS * 86_400_000).toISOString(), sent_to: input.email ? maskEmail(input.email) : null }, meta, 201)
})

/** PUT /public/forms/:key/sessions/:token — save the answers so far (and send the link when an email is given). */
export const saveDraft = defineMockRoute(({ event, body }) => {
  const { form } = resumable(event)
  const token = getRouterParam(event, 'token') ?? ''
  const draft = draftOf(token, form.id)
  if (!draft) throw new MockError('FRM-GEN-1004')
  if (draft.closed) throw new MockError('FRM-RESP-1003')
  const input = parseBody(draftBody, body)
  putDraft(token, { ...draft, data: input.data, page: input.page, email: input.email ?? draft.email, updated_at: new Date().toISOString() })
  const meta = import.meta.dev && input.email ? { dev_resume_url: resumeLink(event, form.public_key, token) } : {}
  return ok({ saved_at: new Date().toISOString(), expires_at: draft.expires_at, sent_to: input.email ? maskEmail(input.email) : null }, meta)
})

/** GET /public/forms/:key/sessions/:token — the saved answers and page. */
export const getDraft = defineMockRoute(({ event }) => {
  const { form } = resumable(event)
  const draft = draftOf(getRouterParam(event, 'token') ?? '', form.id)
  if (!draft) throw new MockError('FRM-GEN-1004')
  if (draft.closed) throw new MockError('FRM-RESP-1003')
  return ok({ data: draft.data, page: draft.page, updated_at: draft.updated_at, expires_at: draft.expires_at })
})

// ── Files for file questions (F10 M2) ───────────────────────────────────────────────────
// The browser uploads straight to storage through a short-lived link, with progress; the answer
// only keeps a reference per file. The submission is checked against these uploads.
const uploadBody = z.object({
  field: z.string().min(1).max(64),
  file_name: z.string().min(1).max(200),
  content_type: z.string().max(120),
  size: z.number().int().positive(),
})
const uploadsBy = new Map<string, number[]>()
const UPLOADS_PER_10_MIN = 60

/** POST /public/forms/:key/uploads — a pre-signed upload link for one file. */
export const requestUpload = defineMockRoute(({ event, body }) => {
  const { tenant, form, schema } = takingResponses(event, getRouterParam(event, 'key') ?? '')
  const input = parseBody(uploadBody, body)
  const field = allFields(schema).find(item => item.key === input.field)
  if (!field || !isFileField(field.type) || isLocked(field)) throw new MockError('FRM-GEN-1002', [{ field: 'field', message: 'This question takes no files.' }])

  // At most 60 files per 10 minutes from one address for one form.
  const who = `${form.id}:${getRequestIP(event, { xForwardedFor: true }) ?? 'unknown'}`
  const recent = (uploadsBy.get(who) ?? []).filter(at => at > Date.now() - 600_000)
  if (recent.length >= UPLOADS_PER_10_MIN) throw new MockError('FRM-GEN-1029')
  uploadsBy.set(who, [...recent, Date.now()])

  const props = (field.props ?? {}) as Record<string, unknown>
  const accept = field.type === 'image_upload' ? String(props.accept || 'image/*') : String(props.accept ?? '')
  const file = { name: input.file_name, type: input.content_type }
  const image = field.type === 'image_upload'
  if (!acceptsFile(accept, file) || (image && (!input.content_type.startsWith('image/') || input.content_type === 'image/svg+xml')))
    throw new MockError('FRM-GEN-1002', [{ field: 'content_type', message: 'This file type is not allowed.' }])
  const maxBytes = maxFileBytes(props)
  if (input.size > maxBytes) throw new MockError('FRM-GEN-1002', [{ field: 'size', message: `The file is larger than ${Math.round(maxBytes / 1024 / 1024)} MB.` }])

  return ok<UploadTicket>(
    createRespondentTicket({
      tenantId: tenant.id,
      formId: form.id,
      field: field.key,
      name: input.file_name,
      contentType: input.content_type,
      size: input.size,
      maxBytes,
      kind: image ? 'image' : 'file',
      listed: parseAccept(accept).filter(type => type.startsWith('.')),
    }),
    {},
    201,
  )
})

/** POST /public/forms/:key/uploads/:id/complete — the stored file → its answer. */
export const completeUpload = defineMockRoute(({ event }) => {
  const { form } = takingResponses(event, getRouterParam(event, 'key') ?? '')
  const answer = completeRespondentUpload(getRouterParam(event, 'id') ?? '', form.id)
  if (!answer) throw new MockError('FRM-GEN-1004')
  return ok<FileAnswer>(answer)
})

// ── Spam check (decision 89) ─────────────────────────────────────────────────────────────
// A signed proof-of-work challenge per fill-in: issued when the form opens, solved in the
// background by the browser, used once. No third-party captcha, no tracking.
const CHALLENGE_SECRET = randomBytes(32)
const CHALLENGE_DIFFICULTY = 14
const CHALLENGE_TTL_MS = 4 * 3_600_000
/** People need a few seconds to fill in a form; bots send at once. */
const MIN_FILL_MS = 3_000
const usedChallenges = new Map<string, number>()
const submitsBy = new Map<string, number[]>()
const SUBMITS_PER_10_MIN = 20

const sign = (payload: string) => createHmac('sha256', CHALLENGE_SECRET).update(payload).digest('base64url')

/** The challenge's salt when the proof is valid for this form (not used before, old enough, not expired). */
async function provenHuman(key: string, proof: { token: string; nonce: number } | undefined): Promise<string | null> {
  if (!proof) return null
  const [encoded, signature] = proof.token.split('.')
  if (!encoded || !signature) return null
  const expected = Buffer.from(sign(encoded))
  const given = Buffer.from(signature)
  if (expected.length !== given.length || !timingSafeEqual(expected, given)) return null
  const [formKey, salt, issued, difficulty] = Buffer.from(encoded, 'base64url').toString('utf8').split('|')
  const age = Date.now() - Number(issued)
  if (formKey !== key || !salt || !(age >= MIN_FILL_MS && age <= CHALLENGE_TTL_MS)) return null
  for (const [used, until] of usedChallenges) if (until < Date.now()) usedChallenges.delete(used)
  if (usedChallenges.has(salt)) return null
  return (await checkWork(salt, Number(difficulty), proof.nonce)) ? salt : null
}

/** POST /public/forms/:key/challenge — a fresh spam-check challenge for this fill-in. */
export const issueChallenge = defineMockRoute(({ event }) => {
  const { form } = takingResponses(event, getRouterParam(event, 'key') ?? '')
  const salt = randomBytes(16).toString('base64url')
  const encoded = Buffer.from([form.public_key, salt, Date.now(), CHALLENGE_DIFFICULTY].join('|')).toString('base64url')
  return ok({ token: `${encoded}.${sign(encoded)}`, salt, difficulty: CHALLENGE_DIFFICULTY, min_wait_ms: MIN_FILL_MS })
})

// ── Short links (F10 M3) ────────────────────────────────────────────────────────────────
/** Where a short link leads (the visit is counted): the form's current link on its own host. */
export function resolveShortLink(event: Parameters<typeof tenantOf>[0], code: string): string {
  const found = SHORT_CODE_PATTERN.test(code) ? findByShortCode(MOCK_TENANTS.filter(item => item.status !== 'suspended'), code) : null
  if (!found) throw new MockError('FRM-FORM-1001')
  const { tenant, form } = found
  form.short_clicks = (form.short_clicks ?? 0) + 1
  saveForms()
  const port = getRequestHost(event, { xForwardedHost: true }).split(':')[1] ?? ''
  return formLink(publicHosts(useRuntimeConfig(event).public, port), form.custom_link || form.public_key, 'fill', tenant.subdomain ?? null)
}

/** GET /public/short/:code — `{ target }` (browser fallback; the server-rendered /s/{code} page redirects itself). */
export const getShortLink = defineMockRoute(({ event }) => ok({ target: resolveShortLink(event, getRouterParam(event, 'code') ?? '') }))

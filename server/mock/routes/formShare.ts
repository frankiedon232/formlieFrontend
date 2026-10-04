/**
 * Share settings (F10 M3, docs/API-CONTRACT.md → Sharing):
 *   GET  /forms/:id/share               access, password set?, response limit, custom link, availability
 *   PUT  /forms/:id/share               change them (row_version) — audited as forms.shared, never the password
 *   GET  /forms/:id/share/link-check    is a custom link free? (+ a free suggestion)
 * Passwords are stored as scrypt hashes; changing one signs everyone out of the form (version).
 */
import { randomBytes, scryptSync } from 'node:crypto'
import { z } from 'zod'
import type { AuditChange } from '#shared/types/audit'
import type { CustomLinkCheck, FormShareSettings } from '#shared/types/forms'
import { customLinkProblem, FORM_KEY_PATTERN } from '#shared/utils/urls/public'
import { requireAuth } from '../core/auth'
import { actorOf, recordAudit } from '../core/audit'
import { MockError, ok } from '../core/respond'
import { defineMockRoute } from '../core/route'
import { parseBody } from '../core/validate'
import { formsOf, saveForms, type StoredForm } from '../data/formStore'
import { MOCK_TENANTS, type MockTenant } from '../data/tenants'

function findForm(tenant: MockTenant, id: string | undefined): StoredForm {
  const form = formsOf(tenant).forms.find(item => item.id === id && !item.deleted_at)
  if (!form) throw new MockError('FRM-GEN-1004')
  return form
}

export const hashPassword = (password: string, salt: string) => scryptSync(password, salt, 32).toString('base64')

const settingsOf = (form: StoredForm): FormShareSettings => ({
  access: form.access ?? 'public',
  has_password: !!form.password,
  password_changed_at: form.password?.changed_at ?? null,
  response_limit: form.response_limit ?? null,
  responses_count: form.responses_count,
  custom_link: form.custom_link ?? null,
  opens_at: form.opens_at,
  closes_at: form.closes_at,
  row_version: form.row_version,
})

/** Who already uses this link (any workspace: forms.* serves them all) — or a form's key that reads the same. */
function linkTaken(value: string, exceptId: string): boolean {
  return MOCK_TENANTS.some(tenant =>
    formsOf(tenant).forms.some(form => form.id !== exceptId && !form.deleted_at && (form.custom_link === value || form.public_key === value)),
  )
}

function check(value: string, formId: string): CustomLinkCheck {
  const problem = customLinkProblem(value)
  if (problem) return { value, available: false, reason: problem, suggestion: null }
  if (!linkTaken(value, formId)) return { value, available: true, reason: null, suggestion: null }
  let n = 2
  while (linkTaken(`${value}-${n}`, formId)) n++
  return { value, available: false, reason: 'taken', suggestion: `${value}-${n}`.slice(0, 60) }
}

/** GET /forms/:id/share */
export const getShare = defineMockRoute(({ event }) => {
  const { tenant } = requireAuth(event)
  return ok(settingsOf(findForm(tenant, getRouterParam(event, 'id'))))
})

/** GET /forms/:id/share/link-check?value= */
export const checkLink = defineMockRoute(({ event }) => {
  const { tenant } = requireAuth(event)
  const form = findForm(tenant, getRouterParam(event, 'id'))
  const value = String(getQuery(event).value ?? '').slice(0, 80)
  return ok(check(value, form.id))
})

const shareSchema = z.object({
  row_version: z.number().int().optional(),
  access: z.enum(['public', 'password']).optional(),
  /** A new password (8–100 characters); never returned. */
  password: z.string().min(8).max(100).optional(),
  response_limit: z.number().int().min(1).max(1_000_000).nullable().optional(),
  custom_link: z.string().max(80).nullable().optional(),
})

/** PUT /forms/:id/share */
export const saveShare = defineMockRoute(({ event, body }) => {
  const { user, tenant } = requireAuth(event)
  const form = findForm(tenant, getRouterParam(event, 'id'))
  const input = parseBody(shareSchema, body)
  if (input.row_version !== undefined && input.row_version !== form.row_version) throw new MockError('FRM-GEN-1009')
  const changes: AuditChange[] = []

  if (input.password !== undefined) {
    const salt = randomBytes(16).toString('base64')
    form.password = { hash: hashPassword(input.password, salt), salt, version: (form.password?.version ?? 0) + 1, changed_at: new Date().toISOString() }
    // Never the password itself — only that it changed.
    changes.push({ field: 'password', before: null, after: 'changed' })
  }
  if (input.access !== undefined && input.access !== (form.access ?? 'public')) {
    if (input.access === 'password' && !form.password)
      throw new MockError('FRM-GEN-1002', [{ field: 'password', message: 'Set a password for this form.' }])
    changes.push({ field: 'access', before: form.access ?? 'public', after: input.access })
    form.access = input.access
  }
  if (input.response_limit !== undefined && input.response_limit !== (form.response_limit ?? null)) {
    changes.push({ field: 'response_limit', before: form.response_limit == null ? null : String(form.response_limit), after: input.response_limit == null ? null : String(input.response_limit) })
    form.response_limit = input.response_limit
  }
  if (input.custom_link !== undefined) {
    const value = input.custom_link?.trim() || null
    if (value !== (form.custom_link ?? null)) {
      if (value) {
        const result = check(value, form.id)
        if (!result.available)
          throw new MockError(result.reason === 'taken' ? 'FRM-FORM-1006' : 'FRM-GEN-1002', [{ field: 'custom_link', message: result.reason ?? 'invalid' }])
        // A link that reads like a key would be ambiguous.
        if (FORM_KEY_PATTERN.test(value) && /[A-Z]/.test(value)) throw new MockError('FRM-GEN-1002', [{ field: 'custom_link', message: 'invalid' }])
      }
      changes.push({ field: 'custom_link', before: form.custom_link ?? null, after: value })
      form.custom_link = value
    }
  }

  if (changes.length) {
    form.row_version++
    form.updated_at = new Date().toISOString()
    saveForms()
    recordAudit(event, tenant, { action: 'forms.shared', actor: actorOf(user), resource: { type: 'form', id: form.id, name: form.name }, changes })
  }
  return ok(settingsOf(form))
})

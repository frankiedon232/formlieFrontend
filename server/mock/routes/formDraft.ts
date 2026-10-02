/**
 * Mock draft / publish / versions for the builder (docs/API-CONTRACT.md → Forms):
 * PUT /forms/:id/draft (autosave, row_version) · POST /forms/:id/publish (checks + new version) ·
 * POST /forms/:id/discard · GET /forms/:id/versions(/:vid) · POST …/versions/:vid/restore.
 * Editing a published form changes only the draft; the published version stays live.
 */
import { z } from 'zod'
import { allFields, publishIssues, starterSchema } from '#shared/utils/forms/build'
import { formSchemaV1, type FormSchemaV1 } from '#shared/utils/forms/schema'
import type { StarterTemplateKey } from '#shared/utils/templates/starters'
import { requireAuth } from '../core/auth'
import { actorOf, recordAudit } from '../core/audit'
import { MockError, ok } from '../core/respond'
import { defineMockRoute } from '../core/route'
import { parseBody } from '../core/validate'
import { formsOf, saveForms, summaryOf, type StoredForm, type StoredVersion } from '../data/formStore'
import type { MockTenant } from '../data/tenants'

const GUESS: [RegExp, StarterTemplateKey][] = [
  [/feedback|nps|evaluation|survey/i, 'customer_feedback'],
  [/event|registration|booking|enrol|volunteer|membership/i, 'event_registration'],
  [/job|application|interview/i, 'job_application'],
  [/onboarding|intake/i, 'employee_onboarding'],
  [/incident|safety|bug|return/i, 'incident_report'],
]

/** Sample forms were seeded without fields: give them a fitting starter the first time they're opened. */
export function ensureSchema(form: StoredForm): FormSchemaV1 {
  if (!form.schema) {
    const key = GUESS.find(([pattern]) => pattern.test(form.name))?.[1] ?? 'contact_lead'
    form.schema = form.template_key
      ? starterSchema(form.template_key as StarterTemplateKey)
      : starterSchema(key)
    if (form.status !== 'draft' && !form.published_schema)
      form.published_schema = structuredClone(form.schema)
    saveForms()
  }
  return form.schema
}

function findForm(tenant: MockTenant, id: string | undefined): StoredForm {
  const form = formsOf(tenant).forms.find(item => item.id === id && !item.deleted_at)
  if (!form) throw new MockError('FRM-GEN-1004')
  return form
}

const versionView = ({ schema: _schema, ...version }: StoredVersion) => version

/** GET /forms/:id/builder — everything the builder needs in one call. */
export const getBuilder = defineMockRoute(({ event }) => {
  const { tenant } = requireAuth(event)
  const form = findForm(tenant, getRouterParam(event, 'id'))
  const schema = ensureSchema(form)
  return ok({
    form: summaryOf(form),
    schema,
    published_version: form.versions?.[0]?.number ?? null,
  })
})

// Draft saves are frequent: one audit entry per form and person per 10 minutes.
const lastDraftAudit = new Map<string, number>()

const draftSchema = z.object({ row_version: z.number().int(), schema: formSchemaV1 })

export const saveDraft = defineMockRoute(({ event, body }) => {
  const { user, tenant } = requireAuth(event)
  const form = findForm(tenant, getRouterParam(event, 'id'))
  const input = parseBody(draftSchema, body)
  if (input.row_version !== form.row_version) throw new MockError('FRM-GEN-1009')
  form.schema = input.schema
  form.has_unpublished_changes = form.status !== 'draft'
  form.row_version++
  form.updated_at = new Date().toISOString()
  saveForms()
  const key = `${form.id}:${user.id}`
  if (Date.now() - (lastDraftAudit.get(key) ?? 0) > 10 * 60_000) {
    lastDraftAudit.set(key, Date.now())
    recordAudit(event, tenant, {
      action: 'forms.updated',
      actor: actorOf(user),
      resource: { type: 'form', id: form.id, name: form.name },
      metadata: { change: 'draft_edited', fields: String(allFields(input.schema).length) },
    })
  }
  return ok({
    row_version: form.row_version,
    updated_at: form.updated_at,
    has_unpublished_changes: form.has_unpublished_changes,
  })
})

const publishSchema = z.object({
  row_version: z.number().int(),
  change_summary: z.string().trim().max(500).nullable().optional(),
})

export const publishForm = defineMockRoute(({ event, body }) => {
  const { user, tenant } = requireAuth(event)
  const form = findForm(tenant, getRouterParam(event, 'id'))
  const input = parseBody(publishSchema, body)
  if (input.row_version !== form.row_version) throw new MockError('FRM-GEN-1009')
  if (!['draft', 'published'].includes(form.status)) throw new MockError('FRM-FORM-1007')
  const schema = ensureSchema(form)
  const issues = publishIssues(schema)
  if (issues.length)
    throw new MockError(
      'FRM-FORM-1004',
      issues.map(issue => ({ field: issue.field_id ?? 'form', message: issue.code })),
    )
  const before = form.status
  const version: StoredVersion = {
    id: crypto.randomUUID(),
    number: (form.versions?.[0]?.number ?? 0) + 1,
    published_at: new Date().toISOString(),
    published_by: { id: user.id, name: `${user.first_name} ${user.last_name}`.trim() },
    change_summary: input.change_summary || null,
    fields_count: allFields(schema).length,
    schema: structuredClone(schema),
  }
  form.versions = [version, ...(form.versions ?? [])]
  form.published_schema = structuredClone(schema)
  form.status = 'published'
  form.has_unpublished_changes = false
  form.row_version++
  form.updated_at = version.published_at
  saveForms()
  recordAudit(event, tenant, {
    action: 'forms.published',
    actor: actorOf(user),
    resource: { type: 'form', id: form.id, name: form.name },
    changes: before !== 'published' ? [{ field: 'status', before, after: 'published' }] : [],
    metadata: {
      version: String(version.number),
      ...(version.change_summary ? { summary: version.change_summary } : {}),
    },
  })
  return ok({ form: summaryOf(form), version: versionView(version) })
})

/** POST /forms/:id/discard — throw away draft changes, back to the published version. */
export const discardDraft = defineMockRoute(({ event }) => {
  const { user, tenant } = requireAuth(event)
  const form = findForm(tenant, getRouterParam(event, 'id'))
  if (!form.published_schema) throw new MockError('FRM-FORM-1007')
  form.schema = structuredClone(form.published_schema)
  form.has_unpublished_changes = false
  form.row_version++
  form.updated_at = new Date().toISOString()
  saveForms()
  recordAudit(event, tenant, {
    action: 'forms.updated',
    actor: actorOf(user),
    resource: { type: 'form', id: form.id, name: form.name },
    metadata: { change: 'draft_discarded' },
  })
  return ok({ form: summaryOf(form), schema: form.schema })
})

export const listVersions = defineMockRoute(({ event }) => {
  const { tenant } = requireAuth(event)
  const form = findForm(tenant, getRouterParam(event, 'id'))
  return ok((form.versions ?? []).map(versionView))
})

export const getVersion = defineMockRoute(({ event }) => {
  const { tenant } = requireAuth(event)
  const form = findForm(tenant, getRouterParam(event, 'id'))
  const version = form.versions?.find(item => item.id === getRouterParam(event, 'vid'))
  if (!version) throw new MockError('FRM-GEN-1004')
  return ok(version)
})

/** POST /forms/:id/versions/:vid/restore — copy a published version into the draft. */
export const restoreVersion = defineMockRoute(({ event }) => {
  const { user, tenant } = requireAuth(event)
  const form = findForm(tenant, getRouterParam(event, 'id'))
  const version = form.versions?.find(item => item.id === getRouterParam(event, 'vid'))
  if (!version) throw new MockError('FRM-GEN-1004')
  form.schema = structuredClone(version.schema)
  form.has_unpublished_changes =
    !!form.published_schema && JSON.stringify(version.schema) !== JSON.stringify(form.published_schema)
  form.row_version++
  form.updated_at = new Date().toISOString()
  saveForms()
  recordAudit(event, tenant, {
    action: 'forms.updated',
    actor: actorOf(user),
    resource: { type: 'form', id: form.id, name: form.name },
    metadata: { change: 'version_restored', version: String(version.number) },
  })
  return ok({ form: summaryOf(form), schema: form.schema })
})

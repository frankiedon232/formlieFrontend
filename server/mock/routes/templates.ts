/**
 * Mock templates (docs/API-CONTRACT.md → Templates, F9): the gallery (system + workspace), one
 * template with its schema, category counts, and the workspace's own templates (save a form as a
 * template, edit, duplicate, delete). System templates can't be changed, duplicate them instead.
 * Every change is in the audit trail.
 */
import { z } from 'zod'
import type { TemplateCategorySummary, TemplateFacets, TemplateSummary } from '#shared/types/templates'
import { TEMPLATE_CATEGORIES, TEMPLATE_CATEGORY_KEYS, categoryOf, templateTheme, translateContent, type TemplateDef } from '#shared/templates'
import type { FormSchemaV1 } from '#shared/utils/forms/schema'
import { APP_LOCALES } from '#shared/utils/i18n/locales'
import { requireAuth } from '../core/auth'
import { requireLevel } from '../data/formPermissions'
import { actorOf, recordAudit } from '../core/audit'
import { MockError, ok, paginate } from '../core/respond'
import { defineMockRoute } from '../core/route'
import { parseBody } from '../core/validate'
import { formsOf } from '../data/formStore'
import { saveLibrary } from '../data/libraryStore'
import { allTemplates, categoryName, findWorkspaceTemplate, translationDict, templateDetail, workspaceKey, workspaceTemplates } from '../data/templateStore'
import type { MockTenant, MockUser } from '../data/tenants'
import { ensureSchema } from './formDraft'

type TemplateAction = 'forms.template_created' | 'forms.template_updated' | 'forms.template_duplicated' | 'forms.template_deleted'
const audit = (
  event: Parameters<typeof recordAudit>[0],
  tenant: MockTenant,
  user: MockUser,
  action: TemplateAction,
  template: { id: string; name: string },
  changes: { field: string; before: string | null; after: string | null }[] = [],
) => recordAudit(event, tenant, { action, actor: actorOf(user), resource: { type: 'template', id: template.id, name: template.name }, changes })

const authorOf = (user: MockUser) => ({ id: user.id, name: `${user.first_name} ${user.last_name}`.trim() })
const langOf = (query: Record<string, unknown>) => (typeof query.lang === 'string' ? query.lang : 'en')
const filterList = (query: Record<string, unknown>, key: string) => {
  const raw = query[`filter[${key}]`] ?? query[key]
  return raw ? String(raw).split(',').filter(Boolean) : null
}

function assertName(tenant: MockTenant, name: string, except?: string) {
  if (workspaceTemplates(tenant).some(item => item.id !== except && item.name.toLowerCase() === name.toLowerCase()))
    throw new MockError('FRM-FORM-1012', [{ field: 'name', message: 'A template with this name exists.' }])
}
function ownTemplate(tenant: MockTenant, key: string | undefined) {
  if (key && !key.startsWith('ws_') && templateDetail(tenant, key, 'en')) throw new MockError('FRM-FORM-1011')
  const item = key ? findWorkspaceTemplate(tenant, key) : undefined
  if (!item) throw new MockError('FRM-GEN-1004')
  return item
}

/** GET /templates, gallery: search (in the person's language), category / source / feature filters, sort. */
export const listTemplates = defineMockRoute(({ event, query }) => {
  const { tenant } = requireAuth(event)
  const category = filterList(query, 'category')
  const source = filterList(query, 'source')
  const features = filterList(query, 'features')
  const fromForm = filterList(query, 'form')
  const items = allTemplates(tenant, langOf(query)).filter(
    item =>
      (!category || category.includes(item.category)) &&
      (!fromForm || (!!item.source_form_id && fromForm.includes(item.source_form_id))) &&
      (!source || source.includes(item.source)) &&
      (!features ||
        features.every(feature => (feature === 'calculations' ? item.calculations_count > 0 : feature === 'logic' ? item.logic_count > 0 : true))),
  )
  const { data, meta } = paginate<TemplateSummary>(
    items,
    { sort: '-forms_count', ...query },
    (item, q) =>
      item.name.toLowerCase().includes(q) ||
      item.description.toLowerCase().includes(q) ||
      item.tags.some(tag => tag.includes(q)) ||
      item.key.includes(q.replace(/\s+/g, '_')),
  )
  return ok(data, meta)
})

/** GET /templates/categories, Formalie's categories with counts and use of the templates inside. */
export const listTemplateCategories = defineMockRoute(({ event, query }) => {
  const { tenant } = requireAuth(event)
  const lang = langOf(query)
  const system = allTemplates(tenant, lang).filter(item => item.source === 'system')
  const rows: TemplateCategorySummary[] = TEMPLATE_CATEGORIES.map(category => {
    const inside = system.filter(item => item.category === category.key).sort((a, b) => b.forms_count - a.forms_count)
    return {
      key: category.key,
      name: categoryName(lang, category.key),
      icon: category.icon,
      templates_count: inside.length,
      calculations_count: inside.filter(item => item.calculations_count > 0).length,
      logic_count: inside.filter(item => item.logic_count > 0).length,
      forms_count: inside.reduce((sum, item) => sum + item.forms_count, 0),
      responses_count: inside.reduce((sum, item) => sum + item.responses_count, 0),
      last_used_at: inside.reduce<string | null>((last, item) => (item.last_used_at && (!last || item.last_used_at > last) ? item.last_used_at : last), null),
      theme: templateTheme({ category: category.key } as TemplateDef, { logo_url: tenant.logo_url ?? null, primary: tenant.brand_color ?? null }) as unknown as Record<string, unknown>,
      examples: inside.slice(0, 3).map(item => item.name),
    }
  }).filter(row => row.templates_count > 0)
  const { data, meta } = paginate<TemplateCategorySummary>(
    rows,
    { sort: '-forms_count', ...query },
    (row, q) => row.name.toLowerCase().includes(q) || row.examples.some(name => name.toLowerCase().includes(q)),
  )
  return ok(data, meta)
})

/** GET /templates/facets, counts per category for the filter. */
export const templateFacets = defineMockRoute(({ event }) => {
  const { tenant } = requireAuth(event)
  const items = allTemplates(tenant, 'en')
  const facets: TemplateFacets = {
    total: items.length,
    categories: Object.fromEntries(TEMPLATE_CATEGORY_KEYS.map(key => [key, items.filter(item => item.category === key).length])),
    workspace: items.filter(item => item.source === 'workspace').length,
  }
  return ok(facets)
})

/** GET /templates/:key, one template with its schema and calculations. */
export const getTemplate = defineMockRoute(({ event, query }) => {
  const { tenant } = requireAuth(event)
  const detail = templateDetail(tenant, getRouterParam(event, 'key') ?? '', langOf(query))
  if (!detail) throw new MockError('FRM-GEN-1004')
  return ok(detail)
})

const createBody = z.object({
  form_id: z.string().min(1),
  name: z.string().trim().min(1).max(80),
  description: z.string().trim().max(300).default(''),
  category: z.enum(TEMPLATE_CATEGORY_KEYS),
})

/** POST /templates, save a form (its current draft, design included) as a workspace template. */
export const createTemplate = defineMockRoute(({ event, body: raw }) => {
  const { user, tenant } = requireAuth(event)
  const input = parseBody(createBody, raw)
  const form = formsOf(tenant).forms.find(item => item.id === input.form_id && !item.deleted_at)
  if (!form) throw new MockError('FRM-GEN-1004')
  // Saving a form as a template copies its content: editors only (decision 97).
  requireLevel(form, user, 'edit')
  assertName(tenant, input.name)
  const now = new Date().toISOString()
  const item = {
    id: crypto.randomUUID().slice(0, 12),
    name: input.name,
    description: input.description,
    category: input.category,
    icon: categoryOf(input.category)?.icon ?? 'i-lucide-layout-template',
    schema: structuredClone(ensureSchema(form, tenant)),
    source_form_id: form.id,
    created_by: authorOf(user),
    created_at: now,
    updated_at: now,
  }
  workspaceTemplates(tenant).unshift(item)
  saveLibrary()
  audit(event, tenant, user, 'forms.template_created', item, [{ field: 'form', before: null, after: form.name }])
  return ok(templateDetail(tenant, workspaceKey(item.id), 'en'), {}, 201)
})

/** PATCH /templates/:key, name, description, category (workspace templates only). */
export const updateTemplate = defineMockRoute(({ event, body: raw }) => {
  const { user, tenant } = requireAuth(event)
  const input = parseBody(createBody.omit({ form_id: true }).partial(), raw)
  const item = ownTemplate(tenant, getRouterParam(event, 'key'))
  if (input.name) assertName(tenant, input.name, item.id)
  const changes = (['name', 'description', 'category'] as const)
    .filter(field => input[field] !== undefined && input[field] !== item[field])
    .map(field => ({ field, before: item[field], after: input[field] ?? null }))
  Object.assign(item, input, input.category ? { icon: categoryOf(input.category)?.icon ?? item.icon } : {}, { updated_at: new Date().toISOString() })
  saveLibrary()
  audit(event, tenant, user, 'forms.template_updated', item, changes)
  return ok(templateDetail(tenant, workspaceKey(item.id), 'en'))
})

/**
 * POST /templates/:key/sync, update a workspace template with the current draft of the form it was
 * saved from (questions, logic, calculations, design); name, description and category stay.
 */
export const syncTemplate = defineMockRoute(({ event }) => {
  const { user, tenant } = requireAuth(event)
  const item = ownTemplate(tenant, getRouterParam(event, 'key'))
  const form = item.source_form_id ? formsOf(tenant).forms.find(entry => entry.id === item.source_form_id && !entry.deleted_at) : undefined
  if (!form) throw new MockError('FRM-GEN-1004')
  requireLevel(form, user, 'edit')
  item.schema = structuredClone(ensureSchema(form, tenant))
  item.updated_at = new Date().toISOString()
  saveLibrary()
  audit(event, tenant, user, 'forms.template_updated', item, [{ field: 'content', before: null, after: form.name }])
  return ok(templateDetail(tenant, workspaceKey(item.id), 'en'))
})

/** POST /templates/:key/duplicate, a workspace copy of any template (system ones included). */
export const duplicateTemplate = defineMockRoute(({ event, query }) => {
  const { user, tenant } = requireAuth(event)
  const source = templateDetail(tenant, getRouterParam(event, 'key') ?? '', langOf(query))
  if (!source) throw new MockError('FRM-GEN-1004')
  let name = `${source.name} (copy)`.slice(0, 80)
  for (let n = 2; workspaceTemplates(tenant).some(item => item.name.toLowerCase() === name.toLowerCase()); n++)
    name = `${source.name} (copy ${n})`.slice(0, 80)
  const now = new Date().toISOString()
  const item = {
    id: crypto.randomUUID().slice(0, 12),
    name,
    description: source.description,
    category: source.category,
    icon: source.icon,
    schema: source.schema,
    created_by: authorOf(user),
    created_at: now,
    updated_at: now,
  }
  workspaceTemplates(tenant).unshift(item)
  saveLibrary()
  audit(event, tenant, user, 'forms.template_duplicated', item, [{ field: 'template', before: null, after: source.name }])
  return ok(templateDetail(tenant, workspaceKey(item.id), 'en'), {}, 201)
})

/** DELETE /templates/:key, forms made from it keep their fields and design. */
export const deleteTemplate = defineMockRoute(({ event }) => {
  const { user, tenant } = requireAuth(event)
  const item = ownTemplate(tenant, getRouterParam(event, 'key'))
  const list = workspaceTemplates(tenant)
  list.splice(list.indexOf(item), 1)
  saveLibrary()
  audit(event, tenant, user, 'forms.template_deleted', item)
  return ok({ deleted: true })
})

// ── Form text in another language (owner, 2026-10-04) ───────────────────────────────────
const translateBody = z.object({
  schema: z.record(z.string(), z.unknown()),
  from: z.string().max(10),
  to: z.string().max(10),
})
const known = (code: string) => (code === 'en' || APP_LOCALES.some(locale => locale.code === code) ? code : null)

/** POST /templates/translate-content, a form's template text in another language (text written by people stays). */
export const translateFormContent = defineMockRoute(({ event, body }) => {
  requireAuth(event)
  const input = parseBody(translateBody, body)
  const from = known(input.from)
  const to = known(input.to)
  if (!from || !to) throw new MockError('FRM-GEN-1002', [{ field: 'to', message: 'Unknown language.' }])
  const result = translateContent(input.schema as unknown as FormSchemaV1, translationDict(from), translationDict(to))
  return ok({ schema: result.schema, translated: result.translated, kept: result.kept.length })
})

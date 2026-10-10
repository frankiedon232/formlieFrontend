/**
 * Mock page designs (docs/API-CONTRACT.md → Page designs; owner 2026-10-04). The page around a form
 * on its public link, in its own library like Themes, three kinds:
 *   system:  Formalie's ready-made designs (read-only; duplicate to change)
 *   saved:   saved from a form's design
 *   created: made in the page editor
 * Forms keep a copy of the tokens plus `schema.page_design_id`, so changing or deleting a design
 * never breaks a form. Every change is in the audit trail.
 */
import { requireResource, resourceActions } from '../data/resourceAccess'
import { z } from 'zod'
import type { PageDesign, PageDesignInsights, ThemeSource } from '#shared/types/forms'
import { PAGE_PRESETS, pageDesignSchema, presetTokens } from '#shared/utils/forms/page-design'
import { defaultTheme } from '#shared/utils/forms/theme'
import { requireAuth } from '../core/auth'
import { actorOf, recordAudit } from '../core/audit'
import { MockError, ok, paginate } from '../core/respond'
import { defineMockRoute } from '../core/route'
import { parseBody } from '../core/validate'
import { formsOf } from '../data/formStore'
import { libraryOf, saveLibrary } from '../data/libraryStore'
import type { MockTenant, MockUser } from '../data/tenants'

const body = z.object({
  name: z.string().trim().min(1).max(80),
  tokens: pageDesignSchema,
  source: z.enum(['saved', 'created']).optional(),
})
const authorOf = (user: MockUser) => ({ id: user.id, name: `${user.first_name} ${user.last_name}`.trim() })
type StoredPage = Omit<PageDesign, 'forms_count' | 'source' | 'name_key'> & { source?: ThemeSource }

function pagesOf(tenant: MockTenant): StoredPage[] {
  const store = libraryOf(tenant)
  store.pages ??= []
  return store.pages as StoredPage[]
}

// ── System designs ─────────────────────────────────────────────────────────────────
const SYSTEM_AUTHOR = { id: 'system', name: 'Formalie' }
const SYSTEM_DATE = '2026-09-01T09:00:00.000Z'
const capital = (key: string) => key.charAt(0).toUpperCase() + key.slice(1).replace(/_/g, ' ')
function systemPages(tenant: MockTenant): StoredPage[] {
  const base = defaultTheme({ logo_url: tenant.logo_url ?? null, primary: tenant.brand_color ?? null })
  return PAGE_PRESETS.map(preset => ({
    id: `sys_page_${preset.key}`,
    name: capital(preset.key),
    tokens: presetTokens(base, preset.patch),
    source: 'system',
    created_by: SYSTEM_AUTHOR,
    created_at: SYSTEM_DATE,
    updated_at: SYSTEM_DATE,
  }))
}
export const SYSTEM_PAGE_COUNT = PAGE_PRESETS.length

/** How many (not deleted) forms currently use each page design. */
function usage(tenant: MockTenant) {
  const counts = new Map<string, number>()
  for (const form of formsOf(tenant).forms)
    if (!form.deleted_at && form.schema?.page_design_id) counts.set(form.schema.page_design_id, (counts.get(form.schema.page_design_id) ?? 0) + 1)
  return counts
}
const view = (tenant: MockTenant, user?: MockUser) => {
  const counts = usage(tenant)
  return (page: StoredPage): PageDesign => ({
    ...page,
    source: page.source ?? 'saved',
    ...(page.source === 'system' ? { name_key: `pages.preset.${page.id.slice(9)}` } : {}),
    forms_count: counts.get(page.id) ?? 0,
    // What this person may do with it (F22 R2 M3: own · all; Formalie's are use-only)
    ...(user ? { can: resourceActions('pages', page, user, tenant) } : {}),
  })
}
const allPages = (tenant: MockTenant) => [...pagesOf(tenant), ...systemPages(tenant)]
function find(tenant: MockTenant, id: string | undefined) {
  const page = allPages(tenant).find(item => item.id === id)
  if (!page) throw new MockError('FRM-GEN-1004')
  return page
}
/** Workspace designs only; Formalie's can't be changed or deleted. */
function own(tenant: MockTenant, id: string | undefined) {
  if (id?.startsWith('sys_')) throw new MockError('FRM-FORM-1014')
  const page = pagesOf(tenant).find(item => item.id === id)
  if (!page) throw new MockError('FRM-GEN-1004')
  return page
}
function assertName(tenant: MockTenant, name: string, except?: string) {
  if (pagesOf(tenant).some(item => item.id !== except && item.name.toLowerCase() === name.toLowerCase()))
    throw new MockError('FRM-FORM-1010', [{ field: 'name', message: 'A page design with this name exists.' }])
}
type PageAction = 'forms.page_design_created' | 'forms.page_design_updated' | 'forms.page_design_deleted'
const audit = (event: Parameters<typeof recordAudit>[0], tenant: MockTenant, user: MockUser, action: PageAction, page: { id: string; name: string }, changes: { field: string; before: string | null; after: string | null }[] = []) =>
  recordAudit(event, tenant, { action, actor: actorOf(user), resource: { type: 'page_design', id: page.id, name: page.name }, changes })

/** GET /page-designs, `filter[source]=system,saved,created`, search, sort. */
export const listPageDesigns = defineMockRoute(({ event, query }) => {
  const { tenant, user } = requireAuth(event)
  const raw = query['filter[source]']
  const sources = typeof raw === 'string' && raw ? raw.split(',') : null
  const all = allPages(tenant).map(view(tenant, user)).filter(page => !sources || sources.includes(page.source))
  const { data, meta } = paginate(all, { sort: '-updated_at', ...query }, (item, q) => item.name.toLowerCase().includes(q))
  return ok(data, meta)
})

/** GET /page-designs/insights, designs per kind and all forms (each card's share of forms). */
export const pageDesignInsights = defineMockRoute(({ event }) => {
  const { tenant, user } = requireAuth(event)
  const all = allPages(tenant).map(view(tenant, user))
  const insights: PageDesignInsights = {
    by_source: { system: 0, saved: 0, created: 0 },
    in_use: all.filter(page => page.forms_count > 0).length,
    forms_total: formsOf(tenant).forms.filter(form => !form.deleted_at).length,
  }
  for (const page of all) insights.by_source[page.source]++
  return ok(insights)
})

/** GET /page-designs/:id, one design (page editor). */
export const getPageDesign = defineMockRoute(({ event }) => {
  const { tenant, user } = requireAuth(event)
  return ok(view(tenant, user)(find(tenant, getRouterParam(event, 'id'))))
})

export const createPageDesign = defineMockRoute(({ event, body: raw }) => {
  const { user, tenant } = requireAuth(event)
  const input = parseBody(body, raw)
  assertName(tenant, input.name)
  const now = new Date().toISOString()
  const page: StoredPage = { id: crypto.randomUUID(), name: input.name, tokens: input.tokens, source: input.source ?? 'saved', created_by: authorOf(user), created_at: now, updated_at: now }
  pagesOf(tenant).unshift(page)
  saveLibrary()
  audit(event, tenant, user, 'forms.page_design_created', page, [{ field: 'source', before: null, after: page.source ?? 'saved' }])
  return ok(view(tenant, user)(page), {}, 201)
})

export const updatePageDesign = defineMockRoute(({ event, body: raw }) => {
  const { user, tenant } = requireAuth(event)
  const input = parseBody(body.partial(), raw)
  const page = own(tenant, getRouterParam(event, 'id'))
  requireResource('pages', 'edit', page, user, tenant)
  if (input.name) assertName(tenant, input.name, page.id)
  const changes = [
    ...(input.name && input.name !== page.name ? [{ field: 'name', before: page.name, after: input.name }] : []),
    ...(input.tokens ? [{ field: 'design', before: null, after: 'updated' }] : []),
  ]
  Object.assign(page, { name: input.name ?? page.name, tokens: input.tokens ?? page.tokens, updated_at: new Date().toISOString() })
  saveLibrary()
  audit(event, tenant, user, 'forms.page_design_updated', page, changes)
  return ok(view(tenant, user)(page))
})

/** POST /page-designs/:id/duplicate, any design (Formalie's included) → a workspace copy to change. */
export const duplicatePageDesign = defineMockRoute(({ event, body: raw }) => {
  const { user, tenant } = requireAuth(event)
  const source = find(tenant, getRouterParam(event, 'id'))
  const wanted = parseBody(z.object({ name: z.string().trim().min(1).max(80).optional() }), raw ?? {}).name
  let name = (wanted ?? `${source.name} (copy)`).slice(0, 80)
  for (let n = 2; pagesOf(tenant).some(item => item.name.toLowerCase() === name.toLowerCase()); n++) name = `${wanted ?? source.name} (copy ${n})`.slice(0, 80)
  const now = new Date().toISOString()
  const copy: StoredPage = {
    id: crypto.randomUUID(),
    name,
    tokens: structuredClone(source.tokens),
    source: source.source === 'system' ? 'created' : (source.source ?? 'saved'),
    created_by: authorOf(user),
    created_at: now,
    updated_at: now,
  }
  pagesOf(tenant).unshift(copy)
  saveLibrary()
  audit(event, tenant, user, 'forms.page_design_created', copy, [{ field: 'copied_from', before: null, after: source.name }])
  return ok(view(tenant, user)(copy), {}, 201)
})

export const deletePageDesign = defineMockRoute(({ event }) => {
  const { user, tenant } = requireAuth(event)
  const list = pagesOf(tenant)
  const page = own(tenant, getRouterParam(event, 'id'))
  requireResource('pages', 'delete', page, user, tenant)
  list.splice(list.indexOf(page), 1)
  saveLibrary()
  audit(event, tenant, user, 'forms.page_design_deleted', page)
  return ok({ id: page.id })
})

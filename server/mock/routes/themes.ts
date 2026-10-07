/**
 * Mock themes (docs/API-CONTRACT.md → Themes). Three kinds (owner, 2026-10-03):
 *   system, Formalie's designs: the designer's starting points and every template category design
 *             (read-only; duplicate to change)
 *   saved:  saved from a form's design ("Save as theme" in the designer)
 *   created, made from scratch in the theme editor
 * Forms keep a copy of the tokens plus `schema.theme_id`, so changing or deleting a theme never
 * breaks a form. Every change is in the audit trail.
 */
import { z } from 'zod'
import type { SavedTheme, ThemeInsights, ThemeSource } from '#shared/types/forms'
import { applyPatch, defaultTheme, themeSchema, THEME_PRESETS } from '#shared/utils/forms/theme'
import { TEMPLATE_CATEGORIES } from '#shared/templates'
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
  tokens: themeSchema,
  source: z.enum(['saved', 'created']).optional(),
})
const authorOf = (user: MockUser) => ({ id: user.id, name: `${user.first_name} ${user.last_name}`.trim() })
type StoredTheme = Omit<SavedTheme, 'forms_count' | 'source' | 'name_key'> & { source?: ThemeSource }

function themesOf(tenant: MockTenant): StoredTheme[] {
  const store = libraryOf(tenant)
  store.themes ??= []
  return store.themes as StoredTheme[]
}

// ── System themes ──────────────────────────────────────────────────────────────────
const SYSTEM_AUTHOR = { id: 'system', name: 'Formalie' }
const SYSTEM_DATE = '2026-09-01T09:00:00.000Z'
const capital = (key: string) => key.charAt(0).toUpperCase() + key.slice(1).replace(/_/g, ' ')
function systemThemes(tenant: MockTenant): StoredTheme[] {
  const base = defaultTheme({ logo_url: tenant.logo_url ?? null, primary: tenant.brand_color ?? null })
  const make = (id: string, name: string, patch: Parameters<typeof applyPatch>[1]): StoredTheme => ({
    id,
    name,
    tokens: applyPatch(base, patch),
    source: 'system',
    created_by: SYSTEM_AUTHOR,
    created_at: SYSTEM_DATE,
    updated_at: SYSTEM_DATE,
  })
  return [
    ...THEME_PRESETS.filter(preset => preset.key !== 'workspace').map(preset => make(`sys_preset_${preset.key}`, capital(preset.key), preset.patch)),
    ...TEMPLATE_CATEGORIES.map(category => make(`sys_category_${category.key}`, `${capital(category.key)} design`, category.design)),
  ]
}
/** i18n key for a system theme's name (the client shows it in the person's language). */
const nameKey = (id: string) =>
  id.startsWith('sys_preset_') ? `designer.preset.${id.slice(11)}` : id.startsWith('sys_category_') ? `templates.categories.${id.slice(13)}` : undefined

/** How many (not deleted) forms currently use each theme. */
function usage(tenant: MockTenant) {
  const counts = new Map<string, number>()
  for (const form of formsOf(tenant).forms)
    if (!form.deleted_at && form.schema?.theme_id) counts.set(form.schema.theme_id, (counts.get(form.schema.theme_id) ?? 0) + 1)
  return counts
}
const view = (tenant: MockTenant) => {
  const counts = usage(tenant)
  return (theme: StoredTheme): SavedTheme => ({
    ...theme,
    source: theme.source ?? 'saved',
    ...(theme.source === 'system' ? { name_key: nameKey(theme.id) } : {}),
    forms_count: counts.get(theme.id) ?? 0,
  })
}
const allThemes = (tenant: MockTenant) => [...themesOf(tenant), ...systemThemes(tenant)]
function find(tenant: MockTenant, id: string | undefined) {
  const theme = allThemes(tenant).find(item => item.id === id)
  if (!theme) throw new MockError('FRM-GEN-1004')
  return theme
}
/** Workspace themes only, system themes can't be changed or deleted. */
function own(tenant: MockTenant, id: string | undefined) {
  if (id?.startsWith('sys_')) throw new MockError('FRM-FORM-1014')
  const theme = themesOf(tenant).find(item => item.id === id)
  if (!theme) throw new MockError('FRM-GEN-1004')
  return theme
}
function assertName(tenant: MockTenant, name: string, except?: string) {
  if (themesOf(tenant).some(item => item.id !== except && item.name.toLowerCase() === name.toLowerCase()))
    throw new MockError('FRM-FORM-1010', [{ field: 'name', message: 'A theme with this name exists.' }])
}
type ThemeAction = 'forms.theme_created' | 'forms.theme_updated' | 'forms.theme_deleted'
const audit = (event: Parameters<typeof recordAudit>[0], tenant: MockTenant, user: MockUser, action: ThemeAction, theme: { id: string; name: string }, changes: { field: string; before: string | null; after: string | null }[] = []) =>
  recordAudit(event, tenant, { action, actor: actorOf(user), resource: { type: 'theme', id: theme.id, name: theme.name }, changes })

/** GET /themes, `filter[source]=system,saved,created`, search, sort. */
export const listThemes = defineMockRoute(({ event, query }) => {
  const { tenant } = requireAuth(event)
  const raw = query['filter[source]']
  const sources = typeof raw === 'string' && raw ? raw.split(',') : null
  const all = allThemes(tenant).map(view(tenant)).filter(theme => !sources || sources.includes(theme.source))
  const { data, meta } = paginate(all, { sort: '-updated_at', ...query }, (item, q) => item.name.toLowerCase().includes(q))
  return ok(data, meta)
})

/** GET /themes/insights, themes per kind, forms styled with a library theme, the most used. */
export const themeInsights = defineMockRoute(({ event }) => {
  const { tenant } = requireAuth(event)
  const all = allThemes(tenant).map(view(tenant))
  const forms = formsOf(tenant).forms.filter(form => !form.deleted_at)
  const ids = new Set(all.map(theme => theme.id))
  const insights: ThemeInsights = {
    by_source: { system: 0, saved: 0, created: 0 },
    in_use: all.filter(theme => theme.forms_count > 0).length,
    forms_total: forms.length,
    forms_styled: forms.filter(form => form.schema?.theme_id && ids.has(form.schema.theme_id)).length,
    top: all
      .filter(theme => theme.forms_count > 0)
      .sort((a, b) => b.forms_count - a.forms_count)
      .slice(0, 3)
      .map(theme => ({ id: theme.id, name: theme.name, ...(theme.name_key ? { name_key: theme.name_key } : {}), forms: theme.forms_count })),
  }
  for (const theme of all) insights.by_source[theme.source]++
  return ok(insights)
})

/** GET /themes/:id, one theme (theme editor). */
export const getTheme = defineMockRoute(({ event }) => {
  const { tenant } = requireAuth(event)
  return ok(view(tenant)(find(tenant, getRouterParam(event, 'id'))))
})

export const createTheme = defineMockRoute(({ event, body: raw }) => {
  const { user, tenant } = requireAuth(event)
  const input = parseBody(body, raw)
  assertName(tenant, input.name)
  const now = new Date().toISOString()
  const theme: StoredTheme = { id: crypto.randomUUID(), name: input.name, tokens: input.tokens, source: input.source ?? 'saved', created_by: authorOf(user), created_at: now, updated_at: now }
  themesOf(tenant).unshift(theme)
  saveLibrary()
  audit(event, tenant, user, 'forms.theme_created', theme, [{ field: 'source', before: null, after: theme.source ?? 'saved' }])
  return ok(view(tenant)(theme), {}, 201)
})

export const updateTheme = defineMockRoute(({ event, body: raw }) => {
  const { user, tenant } = requireAuth(event)
  const input = parseBody(body.partial(), raw)
  const theme = own(tenant, getRouterParam(event, 'id'))
  if (input.name) assertName(tenant, input.name, theme.id)
  const changes = [
    ...(input.name && input.name !== theme.name ? [{ field: 'name', before: theme.name, after: input.name }] : []),
    ...(input.tokens ? [{ field: 'design', before: null, after: 'updated' }] : []),
  ]
  Object.assign(theme, { name: input.name ?? theme.name, tokens: input.tokens ?? theme.tokens, updated_at: new Date().toISOString() })
  saveLibrary()
  audit(event, tenant, user, 'forms.theme_updated', theme, changes)
  return ok(view(tenant)(theme))
})

/** POST /themes/:id/duplicate, any theme (system included) → a workspace copy to change. */
export const duplicateTheme = defineMockRoute(({ event, body: raw }) => {
  const { user, tenant } = requireAuth(event)
  const source = find(tenant, getRouterParam(event, 'id'))
  const wanted = parseBody(z.object({ name: z.string().trim().min(1).max(80).optional() }), raw ?? {}).name
  let name = (wanted ?? `${source.name} (copy)`).slice(0, 80)
  for (let n = 2; themesOf(tenant).some(item => item.name.toLowerCase() === name.toLowerCase()); n++) name = `${wanted ?? source.name} (copy ${n})`.slice(0, 80)
  const now = new Date().toISOString()
  const copy: StoredTheme = {
    id: crypto.randomUUID(),
    name,
    tokens: structuredClone(source.tokens),
    source: source.source === 'system' ? 'created' : (source.source ?? 'saved'),
    created_by: authorOf(user),
    created_at: now,
    updated_at: now,
  }
  themesOf(tenant).unshift(copy)
  saveLibrary()
  audit(event, tenant, user, 'forms.theme_created', copy, [{ field: 'copied_from', before: null, after: source.name }])
  return ok(view(tenant)(copy), {}, 201)
})

export const deleteTheme = defineMockRoute(({ event }) => {
  const { user, tenant } = requireAuth(event)
  const list = themesOf(tenant)
  const theme = own(tenant, getRouterParam(event, 'id'))
  list.splice(list.indexOf(theme), 1)
  saveLibrary()
  audit(event, tenant, user, 'forms.theme_deleted', theme)
  return ok({ id: theme.id })
})

export const SYSTEM_THEME_COUNT = THEME_PRESETS.length - 1 + TEMPLATE_CATEGORIES.length

/** A theme's design for a new form (Settings → Form defaults), or null when it no longer exists. */
export function themeForNewForm(tenant: MockTenant, id: string | null): { id: string; tokens: StoredTheme['tokens'] } | null {
  const theme = id ? allThemes(tenant).find(item => item.id === id) : null
  return theme ? { id: theme.id, tokens: structuredClone(theme.tokens) } : null
}

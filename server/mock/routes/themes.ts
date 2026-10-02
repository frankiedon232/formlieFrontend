/**
 * Mock saved themes (docs/API-CONTRACT.md → Themes): reusable designs per workspace. Forms keep a
 * copy of the tokens plus `schema.theme_id`, so deleting or changing a theme never breaks a form.
 * Every change is in the audit trail.
 */
import { z } from 'zod'
import type { SavedTheme } from '#shared/types/forms'
import { themeSchema } from '#shared/utils/forms/theme'
import { requireAuth } from '../core/auth'
import { actorOf, recordAudit } from '../core/audit'
import { MockError, ok, paginate } from '../core/respond'
import { defineMockRoute } from '../core/route'
import { parseBody } from '../core/validate'
import { formsOf } from '../data/formStore'
import { libraryOf, saveLibrary } from '../data/libraryStore'
import type { MockTenant, MockUser } from '../data/tenants'

const body = z.object({ name: z.string().trim().min(1).max(80), tokens: themeSchema })
const authorOf = (user: MockUser) => ({ id: user.id, name: `${user.first_name} ${user.last_name}`.trim() })

function themesOf(tenant: MockTenant) {
  const store = libraryOf(tenant)
  store.themes ??= []
  return store.themes
}
/** How many (not deleted) forms currently use each theme. */
function usage(tenant: MockTenant) {
  const counts = new Map<string, number>()
  for (const form of formsOf(tenant).forms)
    if (!form.deleted_at && form.schema?.theme_id) counts.set(form.schema.theme_id, (counts.get(form.schema.theme_id) ?? 0) + 1)
  return counts
}
const view = (tenant: MockTenant) => {
  const counts = usage(tenant)
  return (theme: Omit<SavedTheme, 'forms_count'>): SavedTheme => ({ ...theme, forms_count: counts.get(theme.id) ?? 0 })
}
function find(tenant: MockTenant, id: string | undefined) {
  const theme = themesOf(tenant).find(item => item.id === id)
  if (!theme) throw new MockError('FRM-GEN-1004')
  return theme
}
function assertName(tenant: MockTenant, name: string, except?: string) {
  if (themesOf(tenant).some(item => item.id !== except && item.name.toLowerCase() === name.toLowerCase()))
    throw new MockError('FRM-FORM-1010', [{ field: 'name', message: 'A theme with this name exists.' }])
}
const audit = (event: Parameters<typeof recordAudit>[0], tenant: MockTenant, user: MockUser, action: 'forms.theme_created' | 'forms.theme_updated' | 'forms.theme_deleted', theme: { id: string; name: string }, changes: { field: string; before: string | null; after: string | null }[] = []) =>
  recordAudit(event, tenant, { action, actor: actorOf(user), resource: { type: 'theme', id: theme.id, name: theme.name }, changes })

export const listThemes = defineMockRoute(({ event }) => {
  const { tenant } = requireAuth(event)
  const query = getQuery(event)
  const all = themesOf(tenant).map(view(tenant))
  const { data, meta } = paginate(all, { sort: '-updated_at', ...query }, (item, q) => item.name.toLowerCase().includes(q))
  return ok(data, meta)
})

export const createTheme = defineMockRoute(({ event, body: raw }) => {
  const { user, tenant } = requireAuth(event)
  const input = parseBody(body, raw)
  assertName(tenant, input.name)
  const now = new Date().toISOString()
  const theme = { id: crypto.randomUUID(), name: input.name, tokens: input.tokens, created_by: authorOf(user), created_at: now, updated_at: now }
  themesOf(tenant).unshift(theme)
  saveLibrary()
  audit(event, tenant, user, 'forms.theme_created', theme)
  return ok(view(tenant)(theme), {}, 201)
})

export const updateTheme = defineMockRoute(({ event, body: raw }) => {
  const { user, tenant } = requireAuth(event)
  const input = parseBody(body.partial(), raw)
  const theme = find(tenant, getRouterParam(event, 'id'))
  if (input.name) assertName(tenant, input.name, theme.id)
  const changes = [
    ...(input.name && input.name !== theme.name ? [{ field: 'name', before: theme.name, after: input.name }] : []),
    ...(input.tokens ? [{ field: 'design', before: null, after: 'updated' }] : []),
  ]
  Object.assign(theme, input, { updated_at: new Date().toISOString() })
  saveLibrary()
  audit(event, tenant, user, 'forms.theme_updated', theme, changes)
  return ok(view(tenant)(theme))
})

export const duplicateTheme = defineMockRoute(({ event }) => {
  const { user, tenant } = requireAuth(event)
  const source = find(tenant, getRouterParam(event, 'id'))
  let name = `${source.name} (copy)`.slice(0, 80)
  for (let n = 2; themesOf(tenant).some(item => item.name.toLowerCase() === name.toLowerCase()); n++) name = `${source.name} (copy ${n})`.slice(0, 80)
  const now = new Date().toISOString()
  const copy = { ...structuredClone(source), id: crypto.randomUUID(), name, created_by: authorOf(user), created_at: now, updated_at: now }
  themesOf(tenant).unshift(copy)
  saveLibrary()
  audit(event, tenant, user, 'forms.theme_created', copy, [{ field: 'source', before: null, after: source.name }])
  return ok(view(tenant)(copy), {}, 201)
})

export const deleteTheme = defineMockRoute(({ event }) => {
  const { user, tenant } = requireAuth(event)
  const list = themesOf(tenant)
  const theme = find(tenant, getRouterParam(event, 'id'))
  list.splice(list.indexOf(theme), 1)
  saveLibrary()
  audit(event, tenant, user, 'forms.theme_deleted', theme)
  return ok({ id: theme.id })
})

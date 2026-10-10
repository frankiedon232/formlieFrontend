/**
 * Option lists (F7 basics, F15 M1 list manager; docs/API-CONTRACT.md → Option lists, docs/OPTION-LISTS.md).
 * Reusable choice lists per workspace; fields filled from a list remember it (`option_set_id`) and keep
 * a copy of its options, so a form never changes behind its owner's back: "Update forms" copies the
 * list into the drafts that use it (and its translations into the languages each form offers).
 *
 *   GET    /option-lists                       all (builder) · with ?page= the Option sets page (rows, filters, sort)
 *   GET    /option-lists/insights              counts for the page's chart cards
 *   POST   /option-lists                       { name, description?, options }
 *   GET    /option-lists/:id · PATCH · DELETE  (delete: forms keep their copies)
 *   GET    /option-lists/:id/usage             forms and fields using it, and whether they match it
 *   POST   /option-lists/:id/sync              { form_ids? } → copies the list into those drafts
 *   POST   /option-lists/:id/duplicate
 *
 * Values must be different within a list (FRM-FORM-1020). Every change is in the audit trail.
 */
import { requireResource, resourceActions } from '../data/resourceAccess'
import { z } from 'zod'
import type { FormSchemaV1 } from '#shared/utils/forms/schema'
import type { OptionItem, OptionList, OptionListInsights, OptionListRow, OptionListUsage } from '#shared/types/forms'
import { allFields } from '#shared/utils/forms/build'
import { MAX_LARGE_OPTIONS, MAX_LIST_LEVELS, MAX_OPTIONS, keptOnServer, levelCounts, lookupOptions, matchesList, offeredOptions } from '#shared/utils/forms/options'
import { formLanguages, mainLanguage, textHash } from '#shared/utils/forms/translations'
import { actorOf, recordAudit } from '../core/audit'
import { requireAuth } from '../core/auth'
import { MockError, ok, paginate } from '../core/respond'
import { defineMockRoute } from '../core/route'
import { parseBody } from '../core/validate'
import { formsOf, saveForms, type StoredForm } from '../data/formStore'
import { libraryOf, saveLibrary } from '../data/libraryStore'
import { fillLargeLists } from '../data/largeLists'
import type { MockTenant, MockUser } from '../data/tenants'
import type { H3Event } from 'h3'

const name = z.string().trim().min(1).max(80)
const item = z.object({
  value: z.string().trim().min(1).max(200),
  label: z.string().max(500),
  score: z.number().finite().optional(),
  active: z.boolean().optional(),
  translations: z.record(z.string().max(10), z.string().max(500)).optional(),
  level: z.number().int().min(0).max(MAX_LIST_LEVELS - 1).optional(),
  parent: z.string().trim().max(200).optional(),
  attrs: z.record(z.string().max(40), z.union([z.string().max(500), z.number().finite()])).optional(),
})
const level = z.object({ key: z.string().trim().min(1).max(40), label: z.string().trim().min(1).max(60) })
const column = z.object({ key: z.string().trim().min(1).max(40).regex(/^[a-z][a-z0-9_]*$/), label: z.string().trim().min(1).max(60) })
const listBody = z.object({ name, description: z.string().trim().max(300).nullable().optional(), levels: z.array(level).max(MAX_LIST_LEVELS).optional(), columns: z.array(column).max(10).optional(), large: z.boolean().optional(), options: z.array(item).min(1).max(MAX_LARGE_OPTIONS) })
/** A list holds up to 20,000 options, a large list up to 200,000 (F15 M5). */
const assertSize = (count: number, large: boolean) => {
  if (count > (large ? MAX_LARGE_OPTIONS : MAX_OPTIONS)) throw new MockError('FRM-FORM-1022', [{ field: 'options', message: String(count) }])
}

const authorOf = (user: MockUser) => ({ id: user.id, name: `${user.first_name} ${user.last_name}`.trim() })
const audit = (event: H3Event, tenant: MockTenant, user: MockUser, action: 'forms.list_created' | 'forms.list_updated' | 'forms.list_deleted' | 'forms.list_synced', list: { id: string; name: string }, extra: { changes?: { field: string; before: string | null; after: string | null }[]; metadata?: Record<string, string> } = {}) =>
  recordAudit(event, tenant, { action, actor: actorOf(user), resource: { type: 'option_list', id: list.id, name: list.name }, ...extra })

/** Clean items: tidy translations, refuse repeated values; lists with levels: every option sits under one on the level above. */
function cleanOptions(options: OptionItem[], levels: number, columns: string[] = []): OptionItem[] {
  const seen = new Set<string>()
  const byLevel = new Map<number, Set<string>>()
  for (const option of options) {
    const key = option.value.toLowerCase()
    if (seen.has(key)) throw new MockError('FRM-FORM-1020', [{ field: 'options', message: option.value }])
    seen.add(key)
    const at = Math.min(option.level ?? 0, levels - 1)
    if (!byLevel.has(at)) byLevel.set(at, new Set())
    byLevel.get(at)!.add(option.value)
  }
  return options.map(option => {
    const at = levels > 1 ? Math.min(option.level ?? 0, levels - 1) : 0
    if (at > 0 && (!option.parent || !byLevel.get(at - 1)?.has(option.parent))) throw new MockError('FRM-FORM-1021', [{ field: 'options', message: option.label }])
    const translations = Object.fromEntries(Object.entries(option.translations ?? {}).filter(([, text]) => text.trim()))
    // Details only for the list's columns, without empty ones (F15 M4)
    const attrs = Object.fromEntries(Object.entries(option.attrs ?? {}).filter(([key, value]) => columns.includes(key) && value !== '' && value !== null))
    return { value: option.value, label: option.label, ...(option.score !== undefined ? { score: option.score } : {}), ...(option.active === false ? { active: false } : {}), ...(Object.keys(translations).length ? { translations } : {}), ...(at > 0 ? { level: at, parent: option.parent } : {}), ...(Object.keys(attrs).length ? { attrs } : {}) }
  })
}
const cleanLevels = (levels: { key: string; label: string }[] | undefined) => (levels && levels.length > 1 ? levels.map(item => ({ key: item.key, label: item.label })) : undefined)
/** Columns of details (F15 M4): unique keys, at most 10; none = undefined. */
const cleanColumns = (columns: { key: string; label: string }[] | undefined) => {
  const seen = new Set<string>()
  const kept = (columns ?? []).filter(item => !seen.has(item.key) && seen.add(item.key)).map(item => ({ key: item.key, label: item.label }))
  return kept.length ? kept : undefined
}
const assertName = (lists: OptionList[], value: string, except?: string) => {
  if (lists.some(list => list.id !== except && list.name.toLowerCase() === value.toLowerCase())) throw new MockError('FRM-FORM-1009', [{ field: 'name', message: 'taken' }])
}
const findList = (tenant: MockTenant, id: string | undefined) => {
  const list = libraryOf(tenant).lists.find(item => item.id === id)
  if (!list) throw new MockError('FRM-GEN-1004')
  return list
}

// ── Where a list is used ─────────────────────────────────────────────────────────────

function usageOf(tenant: MockTenant, list: OptionList): OptionListUsage[] {
  return formsOf(tenant)
    .forms.filter(form => !form.deleted_at)
    .flatMap(form => {
      const schema = form.schema ?? form.published_schema
      const fields = schema ? allFields(schema).filter(field => field.option_set_id === list.id) : []
      // A large list's fields follow it by themselves (F15 M5)
      return fields.length ? [{ form: { id: form.id, name: form.name, status: form.status }, fields: fields.map(field => ({ id: field.id, key: field.key, label: field.label?.trim() || field.key, in_sync: keptOnServer(list) ? true : matchesList(field.options, list, field.option_level ?? 0) })) }] : []
    })
}

function rowOf(tenant: MockTenant, list: OptionList, languages: string[], user?: MockUser): OptionListRow {
  const usage = usageOf(tenant, list)
  const active = list.options.filter(option => option.active !== false)
  return {
    ...list,
    description: list.description ?? null,
    items_count: active.length,
    retired_count: list.options.length - active.length,
    languages: languages.filter(code => active.length > 0 && active.every(option => option.translations?.[code]?.trim())),
    forms_count: usage.length,
    fields_count: usage.reduce((sum, item) => sum + item.fields.length, 0),
    ...(user ? { can: resourceActions('lists', list, user, tenant) } : {}),
  }
}
const allLanguages = (tenant: MockTenant) => [...new Set(libraryOf(tenant).lists.flatMap(list => list.options.flatMap(option => Object.keys(option.translations ?? {}))))]

// ── Routes ───────────────────────────────────────────────────────────────────────────

export const listOptionLists = defineMockRoute(({ event, query }) => {
  const { tenant, user } = requireAuth(event)
  const lists = [...libraryOf(tenant).lists].sort((a, b) => a.name.localeCompare(b.name))
  // The builder wants them all (large lists: counts per level instead of their options); the Option sets page pages through rows
  if (query.page === undefined) return ok(lists.map(list => ({ ...(keptOnServer(list) ? { ...list, options: [], level_counts: levelCounts(list) } : list), can: resourceActions('lists', list, user, tenant) })))
  const languages = allLanguages(tenant)
  const status = typeof query['filter[status]'] === 'string' ? query['filter[status]'].split(',') : []
  let rows = lists.map(list => rowOf(tenant, list, languages, user))
  if (status.length) rows = rows.filter(row => (status.includes('in_use') && row.forms_count > 0) || (status.includes('unused') && !row.forms_count) || (status.includes('retired') && row.retired_count > 0))
  const sort = typeof query.sort === 'string' ? query.sort : 'name'
  const key = sort.replace(/^-/, '') as 'name' | 'items_count' | 'forms_count' | 'updated_at'
  rows.sort((a, b) => (sort.startsWith('-') ? -1 : 1) * (typeof a[key] === 'number' ? (a[key] as number) - (b[key] as number) : String(a[key]).localeCompare(String(b[key]))))
  const { data, meta } = paginate(rows, { ...query, sort: undefined }, (row, q) => `${row.name} ${row.description ?? ''} ${row.large ? '' : row.options.map(option => option.label).join(' ')}`.toLowerCase().includes(q))
  // Rows show a few options; a large list's are not all sent
  return ok(data.map(row => (keptOnServer(row) ? { ...row, options: row.options.slice(0, 20) } : row)), meta)
})

export const optionListInsights = defineMockRoute(({ event }) => {
  const { tenant, user } = requireAuth(event)
  const languages = allLanguages(tenant)
  const rows = libraryOf(tenant).lists.map(list => rowOf(tenant, list, languages, user))
  return ok<OptionListInsights>({
    total: rows.length,
    in_use: rows.filter(row => row.forms_count > 0).length,
    unused: rows.filter(row => !row.forms_count).length,
    items: rows.reduce((sum, row) => sum + row.items_count, 0),
    retired: rows.reduce((sum, row) => sum + row.retired_count, 0),
    largest: [...rows].sort((a, b) => b.items_count - a.items_count).slice(0, 8).map(row => ({ id: row.id, name: row.name, count: row.items_count })),
  })
})

export const getOptionList = defineMockRoute(({ event }) => {
  const { tenant, user } = requireAuth(event)
  const list = findList(tenant, getRouterParam(event, 'id'))
  return ok(rowOf(tenant, list, allLanguages(tenant), user))
})

export const createOptionList = defineMockRoute(({ event, body }) => {
  const { user, tenant } = requireAuth(event)
  const input = parseBody(listBody, body)
  const store = libraryOf(tenant)
  assertName(store.lists, input.name)
  const now = new Date().toISOString()
  const levels = cleanLevels(input.levels)
  const columns = cleanColumns(input.columns)
  assertSize(input.options.length, !!input.large)
  const created: OptionList = { id: crypto.randomUUID(), name: input.name, description: input.description ?? null, ...(levels ? { levels } : {}), ...(columns ? { columns } : {}), ...(input.large ? { large: true } : {}), options: cleanOptions(input.options, levels?.length ?? 1, columns?.map(item => item.key)), created_by: authorOf(user), created_at: now, updated_at: now }
  store.lists.push(created)
  saveLibrary()
  audit(event, tenant, user, 'forms.list_created', created, { metadata: { options: String(created.options.length) } })
  return ok(created, {}, 201)
})

export const updateOptionList = defineMockRoute(({ event, body }) => {
  const { user, tenant } = requireAuth(event)
  const input = parseBody(listBody.partial(), body)
  const store = libraryOf(tenant)
  const found = findList(tenant, getRouterParam(event, 'id'))
  requireResource('lists', 'edit', found, user, tenant)
  if (input.name) assertName(store.lists, input.name, found.id)
  const levels = input.levels !== undefined ? cleanLevels(input.levels) : found.levels
  const columns = input.columns !== undefined ? cleanColumns(input.columns) : found.columns
  const options = input.options || input.levels !== undefined || input.columns !== undefined ? cleanOptions(input.options ?? found.options, levels?.length ?? 1, columns?.map(item => item.key)) : undefined
  const large = input.large ?? !!found.large
  assertSize((options ?? found.options).length, large)
  const retiredBefore = found.options.filter(option => option.active === false).length
  const changes: { field: string; before: string | null; after: string | null }[] = [
    ...(input.name && input.name !== found.name ? [{ field: 'name', before: found.name, after: input.name }] : []),
    ...(input.description !== undefined && (input.description ?? null) !== (found.description ?? null) ? [{ field: 'description', before: found.description ?? null, after: input.description ?? null }] : []),
    ...(options && options.length !== found.options.length ? [{ field: 'options', before: String(found.options.length), after: String(options.length) }] : []),
    ...(options && options.filter(option => option.active === false).length !== retiredBefore ? [{ field: 'retired', before: String(retiredBefore), after: String(options.filter(option => option.active === false).length) }] : []),
  ]
  if (large !== !!found.large) changes.push({ field: 'large', before: String(!!found.large), after: String(large) })
  const keptBefore = keptOnServer(found)
  if ((levels?.length ?? 1) !== (found.levels?.length ?? 1)) changes.push({ field: 'levels', before: String(found.levels?.length ?? 1), after: String(levels?.length ?? 1) })
  Object.assign(found, { ...(input.name ? { name: input.name } : {}), ...(input.description !== undefined ? { description: input.description ?? null } : {}), ...(options ? { options } : {}), updated_at: new Date().toISOString() })
  if (levels) found.levels = levels
  else delete found.levels
  if (columns) found.columns = columns
  else delete found.columns
  if (large) found.large = true
  else delete found.large
  saveLibrary()
  // Large lists stay on the server: every form using one follows it at once, live forms too (F15 M5)
  // Lists kept on the server (large, or above 20 options): forms follow at once, live forms too, with translations
  if (keptOnServer(found) || keptBefore) {
    let touched = 0
    for (const form of formsOf(tenant).forms.filter(item => !item.deleted_at))
      for (const schema of [form.schema, form.published_schema])
        if (schema && keptOnServer(found)) touched += (syncSchema(schema, found), fillLargeLists(schema, [found], found.id))
        else touched += fillLargeLists(schema, [found], found.id)
    if (touched) saveForms()
  }
  audit(event, tenant, user, 'forms.list_updated', found, { changes })
  return ok(rowOf(tenant, found, allLanguages(tenant), user))
})

export const deleteOptionList = defineMockRoute(({ event }) => {
  const { user, tenant } = requireAuth(event)
  const store = libraryOf(tenant)
  const index = store.lists.findIndex(item => item.id === getRouterParam(event, 'id'))
  if (index < 0) throw new MockError('FRM-GEN-1004')
  requireResource('lists', 'delete', store.lists[index]!, user, tenant)
  const [removed] = store.lists.splice(index, 1)
  saveLibrary()
  // Forms keep their copies of the options; the link just leads nowhere now
  audit(event, tenant, user, 'forms.list_deleted', removed!, { metadata: { forms: String(usageOf(tenant, removed!).length) } })
  return ok({ id: removed!.id })
})

export const optionListUsage = defineMockRoute(({ event }) => {
  const { tenant } = requireAuth(event)
  return ok(usageOf(tenant, findList(tenant, getRouterParam(event, 'id'))))
})

/** Copies the list into a draft: options of every linked field, and label translations for the languages the form offers. */
function syncSchema(schema: FormSchemaV1, list: OptionList): number {
  const languages = formLanguages(schema).filter(code => code !== mainLanguage(schema))
  let changed = 0
  for (const field of allFields(schema).filter(item => item.option_set_id === list.id)) {
    const level = field.option_level ?? 0
    if (!matchesList(field.options, list, level)) changed++
    field.options = offeredOptions(list, level)
    for (const language of languages)
      for (const option of list.options.filter(item => item.active !== false && (item.level ?? 0) === level && item.translations?.[language])) {
        const key = `field.${field.id}.option.${option.value}`
        schema.translations = { ...schema.translations, [language]: { ...schema.translations?.[language], [key]: option.translations![language]! } }
        schema.translated_from = { ...schema.translated_from, [language]: { ...schema.translated_from?.[language], [key]: textHash(option.label) } }
      }
  }
  return changed
}

const syncBody = z.object({ form_ids: z.array(z.string().max(64)).max(500).optional() })

export const syncOptionList = defineMockRoute(({ event, body }) => {
  const { user, tenant } = requireAuth(event)
  const list = findList(tenant, getRouterParam(event, 'id'))
  requireResource('lists', 'edit', list, user, tenant)
  const { form_ids } = parseBody(syncBody, body ?? {})
  const targets = usageOf(tenant, list).filter(item => !form_ids || form_ids.includes(item.form.id))
  let fields = 0
  const touched: StoredForm[] = []
  for (const target of targets) {
    const form = formsOf(tenant).forms.find(item => item.id === target.form.id)
    if (!form?.schema) continue
    const changed = syncSchema(form.schema, list)
    if (!changed) continue
    fields += changed
    form.updated_at = new Date().toISOString()
    form.row_version += 1
    if (form.status === 'published') form.has_unpublished_changes = true
    touched.push(form)
  }
  if (touched.length) {
    saveForms()
    audit(event, tenant, user, 'forms.list_synced', list, { metadata: { forms: String(touched.length), fields: String(fields) } })
  }
  return ok({ forms: touched.length, fields, published: touched.filter(form => form.status === 'published').length })
})

/**
 * GET /option-lists/:id/options?level=&q=&values=&parents= (F15 M5): a large list's options for the builder
 * and previews, as people type: one level, kept to what is under `parents`, at most 50 with the total.
 */
export const lookupListOptions = defineMockRoute(({ event, query }) => {
  const { tenant } = requireAuth(event)
  const list = findList(tenant, getRouterParam(event, 'id'))
  const csv = (value: unknown) => (typeof value === 'string' && value ? value.split(',').slice(0, 500) : null)
  const options = offeredOptions(list, Math.max(0, Math.min(Number(query.level) || 0, MAX_LIST_LEVELS - 1)))
  return ok(lookupOptions(options, { q: String(query.q ?? ''), values: csv(query.values), parents: csv(query.parents) }))
})

export const duplicateOptionList = defineMockRoute(({ event }) => {
  const { user, tenant } = requireAuth(event)
  const store = libraryOf(tenant)
  const source = findList(tenant, getRouterParam(event, 'id'))
  let copyName = `${source.name} (copy)`.slice(0, 80)
  for (let n = 2; store.lists.some(list => list.name.toLowerCase() === copyName.toLowerCase()); n++) copyName = `${source.name} (copy ${n})`.slice(0, 80)
  const now = new Date().toISOString()
  const copy: OptionList = { ...structuredClone(source), id: crypto.randomUUID(), name: copyName, created_by: authorOf(user), created_at: now, updated_at: now }
  store.lists.push(copy)
  saveLibrary()
  audit(event, tenant, user, 'forms.list_created', copy, { metadata: { options: String(copy.options.length), copy_of: source.name } })
  return ok(copy, {}, 201)
})

/**
 * Templates for the mock (F9): the system catalogue (shared/templates) plus each workspace's own
 * templates (library store), usage from the forms made with them, and names in the person's
 * language (read from the app's locale files) and template content in that language
 * (shared/templates/messages) — the real API keeps translations in its database.
 */
import { readFileSync } from 'node:fs'
import { join } from 'node:path'
import type { TemplateCalculation, TemplateDetail, TemplateSummary } from '#shared/types/templates'
import { allFields, blankSchema, starterSchema } from '#shared/utils/forms/build'
import type { FormSchemaV1 } from '#shared/utils/forms/schema'
import { STARTER_TEMPLATE_KEYS, type StarterTemplateKey } from '#shared/utils/templates/starters'
import {
  SYSTEM_TEMPLATES,
  categoryOf,
  localiseSchema,
  previewLabels,
  schemaStats,
  systemTemplate,
  templateSchema,
  type TemplateDef,
} from '#shared/templates'
import { formsOf } from './formStore'
import { libraryOf, type WorkspaceTemplate } from './libraryStore'
import type { MockTenant } from './tenants'

/** Catalogue content date (system templates change with releases). */
const CATALOGUE_DATE = '2026-10-03T08:00:00.000Z'
const SYSTEM_AUTHOR = { id: 'system', name: 'Formalie' }

// ── Names in the person's language ─────────────────────────────────────────────────
const messages = new Map<string, Record<string, unknown>>()
function itemText(lang: string, key: string, part: 'name' | 'description'): string | null {
  const code = /^[a-z]{2}(-[A-Z]{2})?$/.test(lang) ? lang : 'en'
  if (!messages.has(code)) {
    try {
      messages.set(code, JSON.parse(readFileSync(join(process.cwd(), 'i18n', 'locales', `${code}.json`), 'utf8')))
    } catch {
      messages.set(code, {})
    }
  }
  const items = (messages.get(code)?.templates as { items?: Record<string, Record<string, string>> } | undefined)?.items
  return items?.[key]?.[part] ?? null
}

/** A category's name in the person's language. */
export function categoryName(lang: string, key: string): string {
  itemText(lang, '', 'name') // loads the language's messages
  const code = /^[a-z]{2}(-[A-Z]{2})?$/.test(lang) ? lang : 'en'
  const pick = (messages: Record<string, unknown> | undefined) =>
    (messages?.templates as { categories?: Record<string, string> } | undefined)?.categories?.[key]
  if (code !== 'en') itemText('en', '', 'name')
  return pick(messages.get(code)) ?? pick(messages.get('en')) ?? key
}

// ── Template content in the person's language (F9 milestone 5) ───────────────────────
const contents = new Map<string, Record<string, string> | null>()
export function contentDict(code: string): Record<string, string> | null {
  if (code === 'en') return null
  if (!contents.has(code)) {
    try {
      contents.set(code, JSON.parse(readFileSync(join(process.cwd(), 'shared', 'templates', 'messages', `${code}.json`), 'utf8')))
    } catch {
      contents.set(code, null)
    }
  }
  return contents.get(code) ?? null
}
const langCode = (lang: string) => (/^[a-z]{2}(-[A-Z]{2})?$/.test(lang) ? lang : 'en')

type Messages = { builder?: { field?: Record<string, unknown>; defaults?: Record<string, string>; page?: { default?: string } } }
const uiMessages = new Map<string, Messages | null>()
function messagesOf(code: string): Messages | null {
  if (!uiMessages.has(code)) {
    try {
      uiMessages.set(code, JSON.parse(readFileSync(join(process.cwd(), 'i18n', 'locales', `${code}.json`), 'utf8')) as Messages)
    } catch {
      uiMessages.set(code, null)
    }
  }
  return uiMessages.get(code) ?? null
}

/**
 * The builder's own default text (field names given to new questions, "Option 1", "Row 1",
 * "Page 1") English → this language, from the app's message files (owner, 2026-10-04: a new
 * "Long text" question stayed English after changing the form language).
 */
function builderDict(code: string): Record<string, string> {
  const en = messagesOf('en')?.builder
  const local = messagesOf(code)?.builder
  const dict: Record<string, string> = {}
  if (!en || !local) return dict
  for (const [type, text] of Object.entries(en.field ?? {}))
    if (typeof text === 'string' && typeof local.field?.[type] === 'string') dict[text] = local.field[type] as string
  const numbered: [string | undefined, string | undefined][] = [
    [en.defaults?.option, local.defaults?.option],
    [en.defaults?.row, local.defaults?.row],
    [en.page?.default, local.page?.default],
  ]
  for (const [source, target] of numbered)
    if (source && target) for (let n = 1; n <= 50; n++) dict[source.replace('{n}', String(n))] = target.replace('{n}', String(n))
  return dict
}

/** Everything Formalie can move into another language: builder defaults + template text (template wins). */
export function translationDict(code: string): Record<string, string> | null {
  if (code === 'en') return null
  const content = contentDict(code)
  const builder = builderDict(code)
  return content || Object.keys(builder).length ? { ...builder, ...(content ?? {}) } : null
}

/**
 * A blank form in the creator's language (owner, 2026-10-04): the form language, the first page's
 * name and the thank-you text start in it, like forms made from a template.
 */
export function blankFormSchema(lang = 'en'): FormSchemaV1 {
  const code = langCode(lang)
  let page = 'Page 1'
  try {
    const messages = JSON.parse(readFileSync(join(process.cwd(), 'i18n', 'locales', `${code}.json`), 'utf8')) as { builder?: { page?: { default?: string } } }
    page = messages.builder?.page?.default?.replace('{n}', '1') ?? page
  } catch {
    // Unknown language: English.
  }
  return localiseSchema(blankSchema(page), contentDict(code), code)
}
/** A system template's form in the person's language (English when there is no translation). */
function systemSchema(tenant: MockTenant, def: TemplateDef, lang: string) {
  const code = langCode(lang)
  return localiseSchema(templateSchema(def, { logo_url: tenant.logo_url ?? null, primary: tenant.brand_color ?? null }), contentDict(code), code)
}

// ── Workspace templates ────────────────────────────────────────────────────────────
export function workspaceTemplates(tenant: MockTenant): WorkspaceTemplate[] {
  const store = libraryOf(tenant)
  store.templates ??= []
  return store.templates
}
export const workspaceKey = (id: string) => `ws_${id}`
export const findWorkspaceTemplate = (tenant: MockTenant, key: string) =>
  key.startsWith('ws_') ? workspaceTemplates(tenant).find(item => workspaceKey(item.id) === key) : undefined

/** The form a template creates, or null when the key is unknown. */
export function schemaForTemplate(tenant: MockTenant, key: string, lang = 'en'): FormSchemaV1 | null {
  const def = systemTemplate(key)
  if (def) return systemSchema(tenant, def, lang)
  const own = findWorkspaceTemplate(tenant, key)
  if (own) return structuredClone(own.schema)
  // Starters not yet in the catalogue (built in a later milestone).
  if ((STARTER_TEMPLATE_KEYS as string[]).includes(key)) return starterSchema(key as StarterTemplateKey)
  return null
}

// ── Summaries ──────────────────────────────────────────────────────────────────────
function usage(tenant: MockTenant) {
  const byKey = new Map<string, { forms: number; responses: number; last: string | null }>()
  for (const form of formsOf(tenant).forms) {
    if (form.deleted_at || !form.template_key) continue
    const entry = byKey.get(form.template_key) ?? { forms: 0, responses: 0, last: null }
    entry.forms += 1
    entry.responses += form.responses_count
    if (!entry.last || form.created_at > entry.last) entry.last = form.created_at
    byKey.set(form.template_key, entry)
  }
  return byKey
}

function summary(
  base: Pick<TemplateSummary, 'key' | 'source' | 'category' | 'icon' | 'name' | 'description' | 'tags' | 'minutes' | 'created_by' | 'updated_at'> &
    Partial<Pick<TemplateSummary, 'source_form_id'>>,
  schema: FormSchemaV1,
  used?: { forms: number; responses: number; last: string | null },
): TemplateSummary {
  const stats = schemaStats(schema)
  return {
    ...base,
    pages_count: stats.pages,
    fields_count: stats.fields,
    logic_count: stats.logic,
    calculations_count: stats.calculations,
    theme: (schema.theme ?? {}) as Record<string, unknown>,
    preview: previewLabels(schema),
    forms_count: used?.forms ?? 0,
    responses_count: used?.responses ?? 0,
    last_used_at: used?.last ?? null,
    source_form_id: base.source_form_id ?? null,
  }
}

function systemSummary(tenant: MockTenant, def: TemplateDef, lang: string, used: ReturnType<typeof usage>) {
  return summary(
    {
      key: def.key,
      source: 'system',
      category: def.category,
      icon: def.icon,
      name: itemText(lang, def.key, 'name') ?? def.name,
      description: itemText(lang, def.key, 'description') ?? def.description,
      tags: def.tags ?? [],
      minutes: def.minutes,
      created_by: SYSTEM_AUTHOR,
      updated_at: CATALOGUE_DATE,
    },
    systemSchema(tenant, def, lang),
    used.get(def.key),
  )
}

function workspaceSummary(item: WorkspaceTemplate, used: ReturnType<typeof usage>) {
  const key = workspaceKey(item.id)
  return summary(
    {
      key,
      source: 'workspace',
      category: item.category,
      icon: item.icon,
      name: item.name,
      description: item.description,
      tags: [],
      minutes: Math.max(1, Math.round(schemaStats(item.schema).fields / 3)),
      created_by: item.created_by,
      updated_at: item.updated_at,
      source_form_id: item.source_form_id ?? null,
    },
    item.schema,
    used.get(key),
  )
}

export function allTemplates(tenant: MockTenant, lang: string): TemplateSummary[] {
  const used = usage(tenant)
  return [
    ...workspaceTemplates(tenant).map(item => workspaceSummary(item, used)),
    ...SYSTEM_TEMPLATES.map(def => systemSummary(tenant, def, lang, used)),
  ]
}

export function templateDetail(tenant: MockTenant, key: string, lang: string): TemplateDetail | null {
  const used = usage(tenant)
  const def = systemTemplate(key)
  const own = def ? undefined : findWorkspaceTemplate(tenant, key)
  if (!def && !own) return null
  const base = def ? systemSummary(tenant, def, lang, used) : workspaceSummary(own!, used)
  const schema = def ? systemSchema(tenant, def, lang) : structuredClone(own!.schema)
  const calculations: TemplateCalculation[] = allFields(schema)
    .filter(field => field.type === 'calculated')
    .map(field => ({ label: field.label, formula: String(field.props?.formula ?? ''), internal: !!field.props?.internal }))
  return { ...base, schema, calculations }
}

export const isCategory = (key: string) => !!categoryOf(key)

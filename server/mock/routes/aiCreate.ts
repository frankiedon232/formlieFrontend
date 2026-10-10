/**
 * Mock AI assistant, creating (F19 M2, docs/API-CONTRACT.md → AI assistant). Drafts are proposals: they
 * are kept with the request until a person applies (creates the form, template or design) or discards them.
 *
 *   POST /ai/forms/draft          { prompt, document?, pages?, variant?, replaces? } → AiFormDraft (ai.create)
 *   POST /ai/templates/draft      { prompt, variant?, replaces? } → AiTemplateDraft (ai.create)
 *   POST /ai/themes/draft         { colour, mood?, replaces? } → AiThemeDraft (ai.create)
 *   POST /ai/requests/:id/apply   form { name, folder_id? } (forms.create) · template { name, description, category }
 *                                 (forms.save_template) · theme { name, key } (themes.create) → AiApplyResult
 *   POST /ai/requests/:id/discard yours, while it waits for review
 */
import { z } from 'zod'
import { TEMPLATE_CATEGORY_KEYS, schemaStats, templateTheme, type TemplateDef } from '#shared/templates'
import { buildSchema, q } from '#shared/templates/kit'
import type { AiApplyResult, AiFormDraft, AiTemplateDraft, AiThemeDraft } from '#shared/types/ai'
import { AI_KIND_META } from '#shared/utils/ai/kinds'
import { permissionsOf } from '../data/rolesStore'
import { defaultTheme } from '#shared/utils/forms/theme'
import type { FormSchemaV1 } from '#shared/utils/forms/schema'
import { draftForm, rankTemplates } from '../ai/formEngine'
import { themesFromColour } from '../ai/themeEngine'
import { actorOf, recordAudit } from '../core/audit'
import { requireAuth } from '../core/auth'
import { MockError, ok } from '../core/respond'
import { defineMockRoute } from '../core/route'
import { parseBody } from '../core/validate'
import { aiOf, maskText, recordAiRequest, requireAi, saveAi, type StoredAiRequest } from '../data/aiStore'
import { settingsOf } from '../data/settingsStore'
import type { MockTenant, MockUser } from '../data/tenants'
import { createFormFromSchema } from './forms'
import { addWorkspaceTemplate } from './templates'
import { addTheme, themeForNewForm } from './themes'
import { ensureSchema } from './formDraft'
import { requireAction } from '../data/formPermissions'
import { formsOf, saveForms } from '../data/formStore'
import { formTexts, mainLanguage, textHash, walkTexts } from '#shared/utils/forms/translations'
import { APP_LOCALES } from '#shared/utils/i18n/locales'

/** The assistant takes a moment, as the real one does (the page shows its steps meanwhile). */
const thinking = () => new Promise(resolve => setTimeout(resolve, 900))

const branding = (tenant: MockTenant) => {
  const brand = settingsOf(tenant).branding
  return { logo_url: brand.logo_url, primary: brand.brand_color }
}

/** The look a new form gets in this workspace (its default theme, else the default with its brand colour). */
function workspaceLook(tenant: MockTenant) {
  const chosen = themeForNewForm(tenant, settingsOf(tenant).form_defaults.theme_id)
  return chosen?.tokens ?? defaultTheme(branding(tenant))
}

/** A request that was waiting is replaced by "Try again": the old one is marked discarded. */
function replace(tenant: MockTenant, user: MockUser, id: string | null | undefined) {
  if (!id) return
  const old = aiOf(tenant).requests.find(item => item.id === id && item.by.id === user.id && item.status === 'proposed')
  if (old) {
    old.status = 'discarded'
    delete old.output
  }
}

const summaryOf = (stats: ReturnType<typeof schemaStats>) =>
  `A ${stats.pages > 1 ? `${stats.pages}-page ` : ''}draft with ${stats.fields} question${stats.fields === 1 ? '' : 's'}${stats.logic ? `, ${stats.logic} rule${stats.logic === 1 ? '' : 's'}` : ''}${stats.calculations ? ` and ${stats.calculations} calculation${stats.calculations === 1 ? '' : 's'}` : ''}.`

const formInput = z.object({
  prompt: z.string().trim().min(3).max(2000),
  document: z.string().max(20_000).nullish(),
  pages: z.enum(['auto', 'one', 'several']).default('auto'),
  variant: z.number().int().min(0).max(20).default(0),
  replaces: z.string().nullish(),
})

export const draftFormRoute = defineMockRoute(async ({ event, body }) => {
  const { tenant, user } = requireAuth(event)
  const settings = requireAi(tenant, 'form')
  const input = parseBody(formInput, body)
  await thinking()
  const result = draftForm(input)
  const schema: FormSchemaV1 = { ...buildSchema(result.def), theme: workspaceLook(tenant) as unknown as Record<string, unknown> }
  const stats = schemaStats(schema)
  replace(tenant, user, input.replaces)
  const prompt = settings.mask_personal ? maskText(input.prompt) : input.prompt
  const request = recordAiRequest(tenant, user, {
    kind: 'form',
    status: 'proposed',
    title: result.def.name,
    target: null,
    credits: AI_KIND_META.form.credits,
    prompt: input.document ? `${prompt}\n\n(${input.document.split(/\r?\n/).filter(Boolean).length} lines of a document)` : prompt,
    result: summaryOf(stats),
    read: [],
    notes: result.notes,
    stats,
    output: { name: result.def.name, description: result.def.description, schema },
  })
  const draft: AiFormDraft = { request_id: request.id, name: result.def.name, description: result.def.description, schema, notes: result.notes, based_on: result.based_on, source: result.source, stats, credits: request.credits }
  return ok(draft)
})

const templateInput = z.object({
  prompt: z.string().trim().min(3).max(2000),
  variant: z.number().int().min(0).max(20).default(0),
  replaces: z.string().nullish(),
})

export const draftTemplateRoute = defineMockRoute(async ({ event, body }) => {
  const { tenant, user } = requireAuth(event)
  const settings = requireAi(tenant, 'template')
  const input = parseBody(templateInput, body)
  await thinking()
  const result = draftForm({ prompt: input.prompt, pages: 'auto', variant: input.variant })
  // The category of the closest template decides the design (the template gallery's look for that kind)
  const category = (rankTemplates(input.prompt)[0]?.def.category ?? 'business') as TemplateDef['category']
  const def: TemplateDef = { ...result.def, category }
  const schema: FormSchemaV1 = { ...buildSchema(def), theme: templateTheme(def, branding(tenant)) as unknown as Record<string, unknown> }
  const stats = schemaStats(schema)
  replace(tenant, user, input.replaces)
  const request = recordAiRequest(tenant, user, {
    kind: 'template',
    status: 'proposed',
    title: def.name,
    target: null,
    credits: AI_KIND_META.template.credits,
    prompt: settings.mask_personal ? maskText(input.prompt) : input.prompt,
    result: summaryOf(stats),
    read: [],
    notes: result.notes,
    stats,
    output: { name: def.name, description: def.description, category, schema },
  })
  const draft: AiTemplateDraft = { request_id: request.id, name: def.name, description: def.description, category, schema, notes: result.notes, based_on: result.based_on, source: result.source, stats, credits: request.credits }
  return ok(draft)
})

const themeInput = z.object({
  colour: z.string().regex(/^#[0-9a-fA-F]{6}$/),
  mood: z.string().trim().max(200).default(''),
  replaces: z.string().nullish(),
})

/** A short sample form to show designs on. */
const SAMPLE: TemplateDef = {
  key: 'ai_sample',
  category: 'business',
  icon: 'i-lucide-palette',
  minutes: 2,
  name: 'Sample form',
  description: '',
  pages: [{ title: 'About you', rows: [{ fields: [q('full_name', 'Full name', { required: true })] }, { fields: [q('email', 'Email address', { required: true }), q('phone', 'Phone number')] }, { fields: [q('section', 'Your visit')] }, { fields: [q('rating', 'How was your visit?')] }, { fields: [q('long_text', 'Anything we could do better?')] }] }],
}

export const draftThemeRoute = defineMockRoute(async ({ event, body }) => {
  const { tenant, user } = requireAuth(event)
  requireAi(tenant, 'theme')
  const input = parseBody(themeInput, body)
  await thinking()
  const suggestions = themesFromColour(input.colour, input.mood, branding(tenant)).map(item => ({ ...item, tokens: item.tokens as unknown as Record<string, unknown> }))
  replace(tenant, user, input.replaces)
  const request = recordAiRequest(tenant, user, {
    kind: 'theme',
    status: 'proposed',
    title: `Designs from ${input.colour.toUpperCase()}`,
    title_key: { code: 'theme', params: { colour: input.colour.toUpperCase() } },
    target: null,
    credits: AI_KIND_META.theme.credits,
    prompt: `Brand colour ${input.colour.toUpperCase()}${input.mood ? `, ${input.mood}` : ''}`,
    result: `${suggestions.length} designs: ${suggestions.map(item => item.name).join(', ')}. Buttons keep a shade of the colour that white text reads well on.`,
    read: [],
    notes: [{ code: 'themes', params: { n: suggestions.length } }],
    output: { suggestions },
  })
  const draft: AiThemeDraft = { request_id: request.id, colour: input.colour.toLowerCase(), suggestions, sample: buildSchema(SAMPLE), credits: request.credits }
  return ok(draft)
})

function waiting(tenant: MockTenant, user: MockUser, id: string | undefined): StoredAiRequest {
  const request = aiOf(tenant).requests.find(item => item.id === id && item.by.id === user.id)
  if (!request) throw new MockError('FRM-GEN-1004')
  if (request.status !== 'proposed' || !request.output) throw new MockError('FRM-AI-1004')
  return request
}

const applyForm = z.object({ name: z.string().trim().min(1).max(120), folder_id: z.string().nullish() })
const applyTemplate = z.object({ name: z.string().trim().min(1).max(80), description: z.string().trim().max(300).default(''), category: z.enum(TEMPLATE_CATEGORY_KEYS) })
const applyTheme = z.object({ name: z.string().trim().min(1).max(60), key: z.string().min(1) })

export const applyAiRequest = defineMockRoute(({ event, body }) => {
  const { tenant, user } = requireAuth(event)
  const request = waiting(tenant, user, getRouterParam(event, 'id'))
  const can = permissionsOf(user, tenant)
  let result: AiApplyResult
  if (request.kind === 'form') {
    if (!can.has('forms.create')) throw new MockError('FRM-PERM-1001')
    const values = parseBody(applyForm, body)
    const output = request.output as { schema: FormSchemaV1 }
    const { form } = createFormFromSchema(event, tenant, user, { name: values.name, folder_id: values.folder_id, schema: structuredClone(output.schema), source: 'ai' })
    result = { target: { type: 'form', id: form.id, name: form.name } }
  } else if (request.kind === 'template') {
    if (!can.has('forms.save_template')) throw new MockError('FRM-PERM-1001')
    const values = parseBody(applyTemplate, body)
    const output = request.output as { schema: FormSchemaV1 }
    const template = addWorkspaceTemplate(event, tenant, user, { ...values, schema: output.schema })
    result = { target: { type: 'template', id: template.key, name: template.name } }
  } else if (request.kind === 'theme') {
    if (!can.has('themes.create')) throw new MockError('FRM-PERM-1001')
    const values = parseBody(applyTheme, body)
    const suggestion = (request.output as { suggestions: { key: string; tokens: Record<string, unknown> }[] }).suggestions.find(item => item.key === values.key)
    if (!suggestion) throw new MockError('FRM-GEN-1002', [{ field: 'key', message: 'Choose one of the designs.' }])
    const theme = addTheme(event, tenant, user, { name: values.name, tokens: suggestion.tokens as never, source: 'created' })
    result = { target: { type: 'theme', id: theme.id, name: theme.name } }
  } else if ((request.kind === 'translate' || request.kind === 'rewrite') && body && typeof body === 'object' && !('count' in body)) {
    // From the AI pages: into the saved draft, unless the form changed since the assistant read it
    const output = request.output as { form_id: string; row_version: number }
    const form = formsOf(tenant).forms.find(item => item.id === output.form_id && !item.deleted_at)
    if (!form) throw new MockError('FRM-GEN-1004')
    requireAction(form, user, 'edit', tenant)
    if (form.row_version !== output.row_version) throw new MockError('FRM-GEN-1009')
    const schema = ensureSchema(form, tenant)
    const original = new Map(formTexts({ ...schema, settings: { ...schema.settings, title: schema.settings?.title || form.name } }).map(item => [item.key, item.text]))
    let changed = 0
    if (request.kind === 'translate') {
      const values = parseBody(z.object({ translations: z.record(z.string().max(10), z.record(z.string().max(200), z.string().max(50_000))) }), body)
      const main = mainLanguage(schema)
      for (const [code, texts] of Object.entries(values.translations)) {
        if (code === main || !APP_LOCALES.some(locale => locale.code === code)) continue
        const kept = Object.fromEntries(Object.entries(texts).filter(([key, text]) => original.has(key) && text.trim()))
        schema.translations = { ...schema.translations, [code]: { ...schema.translations?.[code], ...kept } }
        schema.translated_from = { ...schema.translated_from, [code]: { ...schema.translated_from?.[code], ...Object.fromEntries(Object.keys(kept).map(key => [key, textHash(original.get(key)!)])) } }
        schema.settings = { ...schema.settings, languages: [...new Set([...(schema.settings?.languages ?? []), code])] }
        changed += Object.keys(kept).length
      }
    } else {
      const values = parseBody(z.object({ texts: z.record(z.string().max(200), z.string().trim().min(1).max(50_000)) }), body)
      walkTexts(schema, (key, text) => {
        if (key === 'form.title' || values.texts[key] === undefined) return text
        changed += 1
        return values.texts[key]!
      })
    }
    form.schema = schema
    form.has_unpublished_changes = form.status !== 'draft'
    form.row_version++
    form.updated_at = new Date().toISOString()
    saveForms()
    recordAudit(event, tenant, { action: 'forms.updated', actor: actorOf(user), resource: { type: 'form', id: form.id, name: form.name }, metadata: { change: request.kind === 'translate' ? 'translated_with_ai' : 'rewritten_with_ai', texts: String(changed) } })
    request.notes = [{ code: 'assist_applied', params: { n: changed, total: changed } }]
    result = { target: { type: 'form', id: form.id, name: form.name } }
  } else if (request.kind === 'builder' || request.kind === 'translate' || request.kind === 'rewrite') {
    // The builder made the changes in the form's draft (saved as usual); this records how many were taken
    const values = parseBody(z.object({ count: z.number().int().min(1).max(500) }), body)
    if (!request.target) throw new MockError('FRM-AI-1004')
    const total = (request.output as { count?: number }).count ?? values.count
    request.result = `${values.count} of ${total} suggestions applied.`
    request.notes = [{ code: 'assist_applied', params: { n: values.count, total } }]
    result = { target: request.target }
  } else throw new MockError('FRM-AI-1004')
  request.status = 'applied'
  request.applied_at = new Date().toISOString()
  request.target = result.target
  delete request.output
  saveAi()
  recordAudit(event, tenant, { action: 'ai.applied', actor: actorOf(user), resource: { type: result.target.type, id: result.target.id, name: result.target.name }, metadata: { kind: request.kind, request: request.title } })
  return ok(result, {}, 201)
})

export const discardAiRequest = defineMockRoute(({ event }) => {
  const { tenant, user } = requireAuth(event)
  const request = waiting(tenant, user, getRouterParam(event, 'id'))
  request.status = 'discarded'
  delete request.output
  saveAi()
  return ok({ discarded: true })
})

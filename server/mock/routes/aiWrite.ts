/**
 * Mock AI assistant, translating and writing (F19 M5, docs/API-CONTRACT.md → AI assistant). Both read the
 * form (the builder's current draft when it sends one, else the saved draft) and propose; nothing changes
 * until the person applies, in the builder or with POST /ai/requests/:id/apply.
 *
 *   POST /ai/forms/:id/translate   { languages [codes], schema? } → AiTranslation (ai.translate; 4 credits a language)
 *   POST /ai/forms/:id/rewrite     { tone (plain · friendly · formal), schema? } → AiRewrite (ai.translate)
 */
import { z } from 'zod'
import { AI_TONES, type AiRewrite, type AiTranslation } from '#shared/types/ai'
import { AI_KIND_META } from '#shared/utils/ai/kinds'
import { APP_LOCALES } from '#shared/utils/i18n/locales'
import { formSchemaV1, type FormSchemaV1 } from '#shared/utils/forms/schema'
import { formTexts, mainLanguage, staleKeys } from '#shared/utils/forms/translations'
import { translatorFor } from '../ai/translator'
import { readingAge, rewrite } from '../ai/writing'
import { requireAuth } from '../core/auth'
import { MockError, ok } from '../core/respond'
import { defineMockRoute } from '../core/route'
import { parseBody } from '../core/validate'
import { recordAiRequest, requireAi } from '../data/aiStore'
import { requireAction } from '../data/formPermissions'
import { formsOf } from '../data/formStore'
import type { MockTenant, MockUser } from '../data/tenants'
import { ensureSchema } from './formDraft'

const thinking = () => new Promise(resolve => setTimeout(resolve, 900))

/** An editable form and the text to work on (with its title, which respondents see too). */
function source(tenant: MockTenant, user: MockUser, id: string | undefined, sent?: FormSchemaV1) {
  const form = formsOf(tenant).forms.find(item => item.id === id && !item.deleted_at)
  if (!form) throw new MockError('FRM-GEN-1004')
  requireAction(form, user, 'edit', tenant)
  const schema = sent ?? ensureSchema(form, tenant)
  const withTitle: FormSchemaV1 = { ...schema, settings: { ...schema.settings, title: schema.settings?.title || form.name } }
  return { form, schema: withTitle }
}

const codes = new Set(APP_LOCALES.map(locale => locale.code))
const translateInput = z.object({ languages: z.array(z.string()).min(1).max(19), schema: formSchemaV1.optional() })

export const translateFormRoute = defineMockRoute(async ({ event, body }) => {
  const { tenant, user } = requireAuth(event)
  const input = parseBody(translateInput, body)
  const { form, schema } = source(tenant, user, getRouterParam(event, 'id'), input.schema)
  const from = mainLanguage(schema)
  const languages = [...new Set(input.languages)].filter(code => codes.has(code) && code !== from)
  if (!languages.length) throw new MockError('FRM-GEN-1002', [{ field: 'languages', message: 'Choose a language other than the form’s own.' }])
  const cost = AI_KIND_META.translate.credits * languages.length
  requireAi(tenant, 'translate', ['forms'], cost)
  await thinking()
  const texts = formTexts(schema)
  const result: AiTranslation['languages'] = languages.map(code => {
    const translate = translatorFor(code)
    const saved = schema.translations?.[code] ?? {}
    const stale = staleKeys(schema, code, texts)
    const items = texts.map(item => {
      const existing = saved[item.key]?.trim() ? saved[item.key]! : null
      // A current translation someone made stays; rich text is left for a person in the mock
      const keep = existing && !stale.has(item.key)
      const translation = keep || item.kind === 'html' ? null : translate(item.text)
      return { key: item.key, text: item.text, kind: item.kind, page: item.page, translation, existing }
    })
    return { code, items, translated: items.filter(item => item.translation).length, missing: items.filter(item => !item.translation && !item.existing).length }
  })
  const request = recordAiRequest(tenant, user, {
    kind: 'translate',
    status: 'proposed',
    title: `Translate ${form.name} into ${languages.join(', ')}`,
    title_key: { code: 'translate', params: { form: form.name, languages: languages.join(',') } },
    target: { type: 'form', id: form.id, name: form.name },
    credits: cost,
    prompt: `Translate the form from ${from} into ${languages.join(', ')}.`,
    result: result.map(item => `${item.code}: ${item.translated} translated, ${item.missing} left`).join('; '),
    read: ['forms'],
    notes: [{ code: 'translated_total', params: { n: result.reduce((sum, item) => sum + item.translated, 0), left: result.reduce((sum, item) => sum + item.missing, 0) } }],
    output: { form_id: form.id, row_version: form.row_version },
  })
  const answer: AiTranslation = { request_id: request.id, form: { id: form.id, name: form.name }, from, languages: result, credits: cost }
  return ok(answer)
})

const rewriteInput = z.object({ tone: z.enum(AI_TONES).default('plain'), schema: formSchemaV1.optional() })

export const rewriteFormRoute = defineMockRoute(async ({ event, body }) => {
  const { tenant, user } = requireAuth(event)
  const input = parseBody(rewriteInput, body)
  const { form, schema } = source(tenant, user, getRouterParam(event, 'id'), input.schema)
  requireAi(tenant, 'rewrite', ['forms'])
  await thinking()
  const english = mainLanguage(schema) === 'en'
  const texts = formTexts(schema).filter(item => item.kind !== 'html' && item.key !== 'form.title')
  const changed = texts.map(item => ({ item, out: rewrite(item.text, input.tone, english) })).filter(entry => entry.out.reasons.length)
  const after = new Map(changed.map(entry => [entry.item.key, entry.out.text]))
  const reading = { before: readingAge(texts.map(item => item.text)), after: readingAge(texts.map(item => after.get(item.key) ?? item.text)) }
  const request = recordAiRequest(tenant, user, {
    kind: 'rewrite',
    status: changed.length ? 'proposed' : 'discarded',
    title: `Rewrite ${form.name} (${input.tone})`,
    title_key: { code: 'rewrite', params: { form: form.name, tone: input.tone } },
    target: { type: 'form', id: form.id, name: form.name },
    credits: AI_KIND_META.rewrite.credits,
    prompt: `Make the form easier to read, ${input.tone} tone.`,
    result: `${changed.length} of ${texts.length} texts could be clearer; reading age ${reading.before} to ${reading.after}.`,
    read: ['forms'],
    notes: [{ code: 'rewrite_result', params: { n: changed.length, total: texts.length, before: reading.before, after: reading.after } }],
    output: { form_id: form.id, row_version: form.row_version },
  })
  const result: AiRewrite = {
    request_id: request.id,
    form: { id: form.id, name: form.name },
    tone: input.tone,
    items: changed.map(({ item, out }) => ({ key: item.key, text: item.text, rewrite: out.text, reasons: out.reasons })),
    reading,
    total: texts.length,
    credits: request.credits,
  }
  return ok(result)
})

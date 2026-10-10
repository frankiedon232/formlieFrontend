/**
 * The mock assistant's help in the builder (F19 M3), on the form as it is being edited:
 *
 *   fields  questions the form is likely missing (from the closest Formalie template, plus common ones)
 *   help    short help texts for questions that have none, by kind of question
 *   logic   follow-ups: details after a yes, "what went wrong" after a low rating, "other" after Other
 *   check   problems: the wrong kind of field for what is asked, duplicates, images without a
 *           description, very long questions, nothing required, choices with too few options, long pages
 *
 * Each result is a suggestion the builder applies or skips. Texts it writes are in English, like the
 * template content. No outside service; the backend's model replaces this.
 */
import { buildSchema, slug, type FieldSeed } from '#shared/templates/kit'
import type { AiAssistAction, AiSuggestion } from '#shared/types/ai'
import { allFields, type FormField } from '#shared/utils/forms/build'
import { isInputField } from '#shared/utils/forms/fields'
import type { FormSchemaV1 } from '#shared/utils/forms/schema'
import { rankTemplates } from './formEngine'

const id = () => `sg_${crypto.randomUUID().slice(0, 8)}`
const norm = (text: string) => slug(text).replace(/_/g, ' ')
const wordsOf = (text: string) => new Set(norm(text).split(' ').filter(word => word.length > 2))
/** Two labels ask the same thing when most of their words match. */
const similar = (a: string, b: string) => {
  const [x, y] = [wordsOf(a), wordsOf(b)]
  if (!x.size || !y.size) return norm(a) === norm(b)
  const shared = [...x].filter(word => y.has(word)).length
  return shared / Math.min(x.size, y.size) >= 0.6
}
const UNIQUE = new Set(['full_name', 'email', 'phone', 'signature', 'consent', 'address'])
const inputs = (schema: FormSchemaV1) => allFields(schema).filter(field => isInputField(field.type) && field.type !== 'hidden' && field.type !== 'calculated')

/** A field the builder can take (fresh id; the builder gives it a clean key from its label). */
function fieldFrom(seed: FieldSeed): FormField {
  const built = allFields(buildSchema({ key: 'x', category: 'business', icon: '', minutes: 1, name: 'x', description: '', pages: [{ title: 'x', rows: [{ fields: [seed] }] }] }))[0]!
  return { ...built, id: `fld_ai${crypto.randomUUID().replace(/-/g, '').slice(0, 10)}`, width: 12 }
}

function suggestFields(schema: FormSchemaV1, name: string): AiSuggestion[] {
  const present = inputs(schema)
  const lastPage = schema.pages.at(-1)!
  const lastField = allFields(schema).at(-1)?.id ?? null
  const out: AiSuggestion[] = []
  const has = (seed: FieldSeed) => present.some(field => (UNIQUE.has(seed.type) && field.type === seed.type) || similar(field.label, seed.label)) || out.some(item => item.kind === 'add_field' && similar(item.field.label, seed.label))
  // The form's name decides the closest template (its questions' words alone mislead: "site rules" is not a site inspection)
  const byName = rankTemplates(name)[0]
  const match = byName && byName.score >= 3 ? byName : null
  if (match)
    for (const page of match.def.pages)
      for (const row of page.rows)
        for (const seed of row.fields) {
          if (out.length >= 5 || !isInputField(seed.type) || seed.type === 'calculated' || seed.type === 'hidden' || has(seed)) continue
          out.push({ id: id(), kind: 'add_field', field: fieldFrom({ ...seed, key: undefined }), page_id: lastPage.id, after_id: lastField, note: { code: 'from_template', params: { name: match.def.name } } })
        }
  const personal = present.some(field => ['email', 'phone', 'address', 'full_name'].includes(field.type))
  const common: FieldSeed[] = [
    ...(!present.some(field => field.type === 'email') && present.some(field => field.type === 'full_name') ? [{ type: 'email' as const, label: 'Email address', required: true }] : []),
    { type: 'long_text', label: 'Anything else you would like to tell us?' },
  ]
  for (const seed of common) if (!has(seed)) out.push({ id: id(), kind: 'add_field', field: fieldFrom(seed), page_id: lastPage.id, after_id: lastField, note: { code: 'common' } })
  const consent: FieldSeed = { type: 'consent', label: 'I agree to my details being used to handle this request', required: true }
  if (personal && !has(consent)) out.push({ id: id(), kind: 'add_field', field: fieldFrom(consent), page_id: lastPage.id, after_id: lastField, note: { code: 'consent' } })
  return out
}

const HELP: Partial<Record<string, (field: FormField) => string>> = {
  email: () => 'We only use this to reply to you.',
  phone: () => 'Include the country code, for example +44 7700 900123.',
  date: field => (/birth/i.test(field.label) ? 'As shown on your ID.' : 'Pick the date from the calendar.'),
  datetime: () => 'Pick the date, then the time.',
  date_range: () => 'Pick the first day, then the last.',
  time: () => 'Use the time where you are.',
  file_upload: field => `PDF, Word or images, up to ${Number(field.props?.max_mb) || 10} MB.`,
  image_upload: field => `A clear photo, up to ${Number(field.props?.max_mb) || 10} MB.`,
  signature: () => 'Sign with your finger, mouse or pen.',
  long_text: () => 'A few sentences is enough.',
  rating: field => `1 is poor, ${Number(field.props?.max) || 5} is excellent.`,
  scale: field => `${Number(field.props?.min) || 0} is the lowest, ${Number(field.props?.max) || 10} the highest.`,
  currency: () => 'Numbers only, without the currency sign.',
  number: () => 'Numbers only.',
  address: () => 'Where we can reach you by post.',
  checkbox: () => 'Choose all that apply.',
  multi_select: () => 'Choose all that apply.',
  ranking: () => 'Drag to put them in order, most important first.',
  url: () => 'The full address, starting with https://',
}

function helpTexts(schema: FormSchemaV1): AiSuggestion[] {
  return inputs(schema)
    .filter(field => !field.help?.trim())
    .flatMap(field => {
      const make = HELP[field.type] ?? (/\b(id|number|reference|code)\b/i.test(field.label) ? () => 'You can find it on your letter or email from us.' : null)
      return make ? [{ id: id(), kind: 'set_help' as const, field_id: field.id, label: field.label, help: make(field) }] : []
    })
}

function logicRules(schema: FormSchemaV1): AiSuggestion[] {
  const list = allFields(schema)
  const targeted = new Set((schema.logic ?? []).flatMap(rule => ((rule as { then?: { target?: string }[] }).then ?? []).map(effect => effect.target)))
  const out: AiSuggestion[] = []
  const rule = (field: FormField, op: string, value: unknown, target: FormField) => ({ id: `rule_ai${crypto.randomUUID().slice(0, 8)}`, when: { all: [{ field: field.id, op, value }] }, then: [{ action: 'show', target: target.id }] })
  for (let i = 0; i < list.length - 1; i++) {
    const field = list[i]!
    const next = list[i + 1]!
    if (targeted.has(next.id) || !isInputField(next.type)) continue
    // A follow-up reads like one ("Please give details", "If yes, which?") or is about the same thing ("Any allergies?" → "Which allergies?")
    const followUp = /\b(details?|describe|explain|which|if yes|if so|specify|tell us more|please give|reason)\b/i.test(next.label) || [...wordsOf(field.label)].some(word => word.length > 3 && wordsOf(next.label).has(word))
    if (field.type === 'toggle' && ['long_text', 'short_text', 'file_upload'].includes(next.type) && followUp)
      out.push({ id: id(), kind: 'add_rule', rule: rule(field, 'true', null, next), note: { code: 'follow_up', params: { field: next.label, after: field.label } } })
    else if ((field.type === 'rating' || field.type === 'scale') && next.type === 'long_text')
      out.push({ id: id(), kind: 'add_rule', rule: rule(field, 'lte', field.type === 'rating' ? 2 : 6, next), note: { code: 'low_rating', params: { field: next.label, after: field.label } } })
    else if (['radio', 'dropdown'].includes(field.type) && next.type === 'short_text') {
      const other = field.options?.find(option => /^other\b/i.test(option.label))
      if (other) out.push({ id: id(), kind: 'add_rule', rule: rule(field, 'eq', other.value, next), note: { code: 'other_option', params: { field: next.label, after: field.label } } })
    }
  }
  return out
}

function check(schema: FormSchemaV1): AiSuggestion[] {
  const out: AiSuggestion[] = []
  const all = allFields(schema)
  const fix = (field: FormField | null, problem: Extract<AiSuggestion, { kind: 'fix' }>['problem'], patch: Partial<FormField> | null, remove = false) =>
    out.push({ id: id(), kind: 'fix', field_id: field?.id ?? null, label: field?.label ?? '', problem, patch, ...(remove ? { remove } : {}) })
  const seen: FormField[] = []
  for (const field of all) {
    const text = field.type === 'short_text'
    if (text && /\be-?mail\b/i.test(field.label)) fix(field, 'email_type', { type: 'email' })
    else if (text && /\b(phone|mobile|telephone)\b/i.test(field.label)) fix(field, 'phone_type', { type: 'phone' })
    else if (text && /\b(date|birthday|dob)\b/i.test(field.label)) fix(field, 'date_type', { type: 'date' })
    else if (text && /\b(how many|number of|quantity|age)\b/i.test(field.label)) fix(field, 'number_type', { type: 'number' })
    if (field.type === 'image' && !String(field.props?.alt ?? '').trim()) fix(field, 'image_alt', { props: { ...field.props, alt: field.label || 'Image' } })
    if (isInputField(field.type) && !field.label.trim()) fix(field, 'no_label', null)
    if (field.label.length > 120) {
      const [first, ...rest] = field.label.split(/(?<=[.?!])\s+/)
      fix(field, 'long_label', rest.length ? { label: first, help: [rest.join(' '), field.help].filter(Boolean).join(' ') } : null)
    }
    if ((field.options?.length ?? 2) < 2 && ['radio', 'dropdown', 'checkbox', 'multi_select', 'ranking'].includes(field.type)) fix(field, 'few_options', null)
    if (isInputField(field.type) && field.label.trim() && seen.some(other => norm(other.label) === norm(field.label) && other.type === field.type)) fix(field, 'duplicate', null, true)
    seen.push(field)
  }
  const askable = inputs(schema)
  if (askable.length && !askable.some(field => field.required)) {
    const first = askable.find(field => ['full_name', 'email'].includes(field.type)) ?? askable[0]!
    fix(first, 'no_required', { required: true })
  }
  for (const page of schema.pages) {
    const count = page.rows.reduce((sum, row) => sum + row.fields.length, 0)
    if (count > 12) out.push({ id: id(), kind: 'fix', field_id: null, label: page.title ?? '', problem: 'long_page', patch: null })
  }
  return out
}

export function assistForm(action: AiAssistAction, schema: FormSchemaV1, name: string): AiSuggestion[] {
  if (action === 'fields') return suggestFields(schema, name)
  if (action === 'help') return helpTexts(schema)
  if (action === 'logic') return logicRules(schema)
  return check(schema)
}

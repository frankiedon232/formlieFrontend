/**
 * The mock assistant's form maker (F19 M2). From a description in plain words, or a pasted document, it
 * builds a TemplateDef (the same kit Formalie's templates are written in) and so a real form schema:
 *
 *   1. A pasted document: every line that reads like a question becomes one (headings start pages).
 *   2. A description that lists what to ask ("name, company, arrival time and a photo"): each item
 *      becomes the field that asks it best (questions.ts), with the person's own words as labels.
 *   3. Otherwise the closest of Formalie's templates, renamed to what was asked for.
 *
 * Then: people's details first when the form is about people, a follow-up shown after a "yes", a total
 * when there is a quantity and a price, pages when it is long, agreement and signature last.
 * `variant` gives another take for "Try again". No outside service; the backend's model replaces it.
 */
import { SYSTEM_TEMPLATES, type TemplateDef } from '#shared/templates'
import { slug, type FieldSeed, type PageSeed, type RuleSeed } from '#shared/templates/kit'
import type { AiNote } from '#shared/types/ai'
import { cleanLabel, seedFor } from './questions'

export interface FormDraftInput {
  prompt: string
  document?: string | null
  /** auto = pages when it is long; one = a single page; several = grouped into pages. */
  pages?: 'auto' | 'one' | 'several'
  variant?: number
}

export interface FormDraftResult {
  def: TemplateDef
  /** What the assistant did (shown with the draft, translated in the app). */
  notes: AiNote[]
  based_on: { key: string; name: string } | null
  source: 'document' | 'list' | 'template' | 'basic'
}

const STOP = new Set('a an and are as at be by for from i in is it me my of on or our the their them they this to us we what with you your form survey please need want make create build new should can that which who will would like about'.split(' '))
const PEOPLE = /\b(visitors?|applicants?|candidates?|employees?|staff|customers?|clients?|patients?|guests?|students?|members?|volunteers?|attendees?|participants?|tenants?|suppliers?|contractors?|parents?|people|users?|respondents?|registrations?|sign-?ups?|bookings?|requests?)\b/i
const KINDS = /\b(form|survey|checklist|application|request|questionnaire|registration|feedback|report|log|booking|order|sign-?in|sign-?up|assessment|inspection|evaluation|review|enquiry|inquiry|claim|poll|quiz)\b/i

const words = (text: string) =>
  text
    .toLowerCase()
    .replace(/[^\p{L}\p{N}\s-]/gu, ' ')
    .split(/\s+/)
    .map(word => word.replace(/(ies)$/, 'y').replace(/(?<!s)s$/, ''))
    .filter(word => word.length > 2 && !STOP.has(word))

/** Formalie's templates, best match first, with a score (0 = nothing in common). */
export function rankTemplates(prompt: string): { def: TemplateDef; score: number }[] {
  const asked = new Set(words(prompt))
  return SYSTEM_TEMPLATES.map(def => {
    const score =
      words(def.name).filter(word => asked.has(word)).length * 3 +
      (def.tags ?? []).flatMap(tag => words(tag)).filter(word => asked.has(word)).length * 2 +
      words(def.description).filter(word => asked.has(word)).length
    return { def, score }
  })
    .filter(item => item.score > 0)
    .sort((a, b) => b.score - a.score)
}

/** "A sign-in form for visitors at reception" → "Visitor sign-in form". */
export function titleFrom(prompt: string, fallback: string): string {
  const first = prompt.split(/[.\n:]/)[0] ?? ''
  const kind = first.match(KINDS)
  if (!kind) return fallback
  const before = first.slice(0, kind.index).replace(/^.*\b(a|an|the|need|want|create|make|build)\b\s*/i, '').trim()
  // "for visitors at reception" → "visitor"; "for new starters" → "new starter"
  const forWho = first.slice((kind.index ?? 0) + kind[0].length).match(/\bfor ((?:new|existing|our|all|the) )?([\p{L}-]+)/u)
  const who = forWho ? `${forWho[1] && !/^(our|all|the) $/.test(forWho[1]) ? forWho[1] : ''}${forWho[2]}` : undefined
  const noun = /\bform$/i.test(kind[0]) ? 'form' : kind[0].toLowerCase()
  const lead = [who && !/\b(the|our|us|people)\b/i.test(who) ? who.replace(/s\b/, '') : '', before].filter(Boolean).join(' ')
  const title = `${lead} ${noun === 'form' || /form$/i.test(lead) ? noun : `${noun}${/form|survey|checklist|request|report|log|order|review|quiz|poll|claim/.test(noun) ? '' : ' form'}`}`.trim()
  const clean = title.replace(/\s+/g, ' ').replace(/\b(form) form\b/i, '$1')
  return clean.length >= 4 ? clean[0]!.toUpperCase() + clean.slice(1).toLowerCase().slice(0, 79) : fallback
}

/** The items a description lists ("name, company, arrival time and a photo"). */
export function listedItems(prompt: string): string[] {
  const lead = prompt.match(/\b(with|including|includes?|asking (?:for|about)|asks? (?:for|about)|collect(?:s|ing)?|capture[sd]?|fields?|questions?|need(?:s)? to know|covering)\b[:\s]+([\s\S]+)/i)
  const text = lead ? lead[2]! : prompt.split(/[,;]/).length >= 4 ? prompt : ''
  if (!text) return []
  return text
    .split(/\n|;|,|\s+and\s+|\s+or\s+|\s+plus\s+|\.\s/)
    .map(part => part.replace(/\b(etc|and so on)\.?$/i, '').trim())
    .filter(part => part.length > 1 && part.split(/\s+/).length <= 9)
}

/** Lines of a pasted document that read like questions; `#`, "Section …" or ALL CAPS lines start a page. */
export function documentQuestions(doc: string): { pages: { title: string; items: string[] }[] } {
  const pages: { title: string; items: string[] }[] = []
  let current = { title: 'Questions', items: [] as string[] }
  for (const raw of doc.split(/\r?\n/)) {
    const line = raw.trim()
    if (!line) continue
    const heading = /^#+\s+/.test(line) || /^(section|part|step)\s+\w+/i.test(line) || (line.length <= 40 && line === line.toUpperCase() && /\p{L}/u.test(line))
    if (heading) {
      if (current.items.length) pages.push(current)
      current = { title: cleanLabel(line.replace(/^#+\s+/, '').toLowerCase()), items: [] }
      continue
    }
    const question = /[?:]\s*$/.test(line) || /_{3,}|\[\s?\]|\(\s?\)/.test(line) || /^[^:]{2,60}:\s*\S+( \/ \S+)+/.test(line) || (/^[-*•\d]/.test(line) && line.length <= 90)
    if (question) current.items.push(line.replace(/_{3,}.*$/, '').replace(/[:]\s*$/, '').trim())
  }
  if (current.items.length) pages.push(current)
  return { pages }
}

/** A choice question written with its answers: "Shift: Morning / Afternoon / Night" or "( ) A ( ) B". */
function withInlineOptions(line: string, seed: FieldSeed): FieldSeed {
  const boxes = [...line.matchAll(/[([]\s?[)\]]\s*([^([]+)/g)].map(match => match[1]!.trim()).filter(Boolean)
  const slashed = line.includes(' / ') ? line.split(/[:?]/).pop()!.split(' / ').map(part => part.trim()).filter(Boolean) : []
  const options = boxes.length >= 2 ? boxes : slashed.length >= 2 ? slashed : []
  if (options.length < 2) return seed
  if (options.length === 2 && options.every(option => /^(yes|no)$/i.test(option))) return { ...seed, type: 'toggle' }
  const label = cleanLabel(line.replace(/[([]\s?[)\]].*$/, '').split(':')[0]!.replace(/\?.*$/, '?'))
  return { type: options.length > 5 ? 'dropdown' : boxes.length && /\[/.test(line) ? 'checkbox' : 'radio', label: label || seed.label, options: options.map(option => ({ value: slug(option), label: option })) }
}

const CONTACT = new Set(['full_name', 'email', 'phone'])
const LAST = new Set(['consent', 'signature'])

function chunk(fields: FieldSeed[], mode: 'auto' | 'one' | 'several'): PageSeed[] {
  const front = fields.filter(field => CONTACT.has(field.type))
  const back = fields.filter(field => LAST.has(field.type))
  const middle = fields.filter(field => !CONTACT.has(field.type) && !LAST.has(field.type))
  const paged = mode === 'several' || (mode === 'auto' && fields.length > 8)
  // Short fields side by side (two per row), long answers and choices on their own
  const rows = (list: FieldSeed[]) => {
    const out: (FieldSeed | { fields: FieldSeed[] })[] = []
    for (let i = 0; i < list.length; i++) {
      const a = list[i]!
      const b = list[i + 1]
      const short = (field: FieldSeed) => ['full_name', 'email', 'phone', 'date', 'time', 'number', 'currency', 'short_text', 'country', 'datetime', 'percentage', 'url', 'language'].includes(field.type)
      if (b && short(a) && short(b) && a.type !== 'full_name') {
        out.push({ fields: [a, b] })
        i++
      } else out.push(a)
    }
    return out
  }
  if (!paged) return [{ title: 'Your answers', rows: rows([...front, ...middle, ...back]).map(item => ('fields' in item ? item : { fields: [item] })) }]
  const pages: { title: string; list: FieldSeed[] }[] = []
  if (front.length) pages.push({ title: 'About you', list: front })
  for (let i = 0; i < middle.length; i += 6) pages.push({ title: middle.length > 6 ? `Details ${i / 6 + 1}` : 'Details', list: middle.slice(i, i + 6) })
  if (back.length) {
    if (pages.length) pages[pages.length - 1]!.list.push(...back)
    else pages.push({ title: 'Confirm', list: back })
  }
  return pages.map(page => ({ title: page.title, rows: rows(page.list).map(item => ('fields' in item ? item : { fields: [item] })) }))
}

/** Follow-ups after a yes ("Any allergies?" → "Please give details") and a total for quantity × price. */
function addLogic(fields: FieldSeed[], notes: AiNote[]): { fields: FieldSeed[]; logic: RuleSeed[] } {
  const logic: RuleSeed[] = []
  const out: FieldSeed[] = []
  const keys = new Set<string>()
  const keyOf = (field: FieldSeed) => {
    let key = slug(field.key ?? field.label)
    if (!/^[a-z]/.test(key)) key = `q_${key}`
    for (let n = 2; keys.has(key); n++) key = `${slug(field.label)}_${n}`
    keys.add(key)
    return key
  }
  for (const field of fields) out.push({ ...field, key: keyOf(field) })
  for (let i = 0; i < out.length - 1; i++) {
    const field = out[i]!
    const next = out[i + 1]!
    if (field.type === 'toggle' && (next.type === 'long_text' || /\b(detail|describe|explain|which|if yes|specify|what)\b/i.test(next.label))) {
      logic.push({ match: 'all', when: [{ key: field.key!, op: 'true' }], then: [{ action: 'show', target: next.key }] })
      notes.push({ code: 'follow_up', params: { field: next.label, after: field.label } })
    }
  }
  const quantity = out.find(field => field.type === 'number' && /\b(quantity|how many|number of|qty)\b/i.test(field.label))
  const price = out.find(field => field.type === 'currency')
  if (quantity && price && !out.some(field => field.type === 'calculated')) {
    const total: FieldSeed = { type: 'calculated', label: 'Total', key: keyOf({ type: 'calculated', label: 'Total' }), formula: `{${quantity.key}} * {${price.key}}`, props: { format: 'currency' } }
    out.splice(out.indexOf(price) + 1, 0, total)
    notes.push({ code: 'total', params: { a: quantity.label, b: price.label } })
  }
  return { fields: out, logic }
}

function fromFields(name: string, prompt: string, fields: FieldSeed[], mode: 'auto' | 'one' | 'several', notes: AiNote[]): TemplateDef {
  const withLogic = addLogic(fields, notes)
  const pages = chunk(withLogic.fields, mode)
  if (pages.length > 1) notes.push({ code: 'pages', params: { n: pages.length } })
  return {
    key: `ai_${slug(name)}`,
    category: 'business',
    icon: 'i-lucide-sparkles',
    minutes: Math.max(1, Math.round(withLogic.fields.length / 3)),
    name,
    description: prompt.slice(0, 200),
    pages,
    logic: withLogic.logic,
    thankYou: { title: 'Thank you!', message: 'Your answers have been sent.' },
  }
}

/** A draft form for a description (and optional document). */
export function draftForm(input: FormDraftInput): FormDraftResult {
  const prompt = input.prompt.trim()
  const mode = input.pages ?? 'auto'
  const variant = input.variant ?? 0
  const notes: AiNote[] = []
  const ranked = rankTemplates(`${prompt} ${input.document ?? ''}`)

  // 1. A pasted document
  if (input.document?.trim()) {
    const parsed = documentQuestions(input.document)
    const items = parsed.pages.flatMap(page => page.items)
    if (items.length) {
      const name = titleFrom(prompt, ranked[0]?.def.name ?? 'Form from a document')
      const seeds = items.map(line => withInlineOptions(line, seedFor(line)))
      notes.push({ code: 'document_questions', params: { n: items.length } })
      if (parsed.pages.length > 1 && mode !== 'one') {
        const def = fromFields(name, prompt, seeds, 'one', notes)
        let at = 0
        def.pages = parsed.pages.map(page => ({ title: page.title, rows: page.items.map(() => ({ fields: [def.pages[0]!.rows.flatMap(row => row.fields)[at++]!] })) }))
        notes.push({ code: 'document_sections', params: { n: parsed.pages.length } })
        return { def, notes, based_on: null, source: 'document' }
      }
      return { def: fromFields(name, prompt, seeds, mode, notes), notes, based_on: null, source: 'document' }
    }
    notes.push({ code: 'document_none' })
  }

  // 2. A description that lists what to ask
  const items = listedItems(prompt)
  if (items.length >= 3) {
    const name = titleFrom(prompt, ranked[0]?.def.name ?? 'New form')
    const seeds = items.map(seedFor)
    const asksPeople = PEOPLE.test(prompt) && !seeds.some(seed => seed.type === 'full_name')
    if (asksPeople && variant % 2 === 0) {
      seeds.unshift({ type: 'full_name', label: 'Full name', required: true })
      if (!seeds.some(seed => seed.type === 'email')) seeds.splice(1, 0, { type: 'email', label: 'Email address', required: true })
      notes.push({ code: 'added_contact' })
    }
    notes.push({ code: 'from_list', params: { n: items.length } })
    return { def: fromFields(name, prompt, seeds, variant % 2 === 1 && mode === 'auto' ? 'several' : mode, notes), notes, based_on: null, source: 'list' }
  }

  // 3. The closest template (another one on "Try again")
  const match = ranked[variant % Math.max(1, ranked.length)]
  if (match && match.score >= 3) {
    const def = structuredClone(match.def)
    def.name = titleFrom(prompt, def.name)
    if (mode === 'one' && def.pages.length > 1) def.pages = [{ title: def.pages[0]!.title, rows: def.pages.flatMap(page => page.rows) }]
    notes.push({ code: 'template', params: { name: match.def.name } })
    if (ranked.length > 1) notes.push({ code: 'try_again' })
    return { def, notes, based_on: { key: match.def.key, name: match.def.name }, source: 'template' }
  }

  // 4. Not much to go on: a basic form to build on
  notes.push({ code: 'basic' })
  return {
    def: fromFields(titleFrom(prompt, 'New form'), prompt, [{ type: 'full_name', label: 'Full name', required: true }, { type: 'email', label: 'Email address', required: true }, { type: 'long_text', label: cleanLabel(prompt).slice(0, 120) || 'Your message' }], mode, notes),
    notes,
    based_on: null,
    source: 'basic',
  }
}

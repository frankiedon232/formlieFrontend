/**
 * Template content in the person's language (F9 milestone 5). Templates are written in English; a
 * dictionary per language (`shared/templates/messages/<code>.json`, English text → translation,
 * shared by all templates so "Email" is translated once) is applied to the built schema. Only text
 * people read changes — keys, option values, scores, logic and formulas stay as they are, so
 * calculations and rules behave the same in every language. Text results inside formulas
 * (`"Pass"`) are translated too; values compared against answers (`{attending} = "yes"`) are not.
 * Missing entries simply stay in English.
 */
import type { FormSchemaV1 } from '../utils/forms/schema'

type Dict = Record<string, string>

/** Field props that hold readable text (every field type: choices, scales, consent, sections, images…). */
const TEXT_PROPS = ['text', 'html', 'description', 'min_label', 'max_label', 'link_label', 'alt', 'caption'] as const
const LITERAL = /"([^"\\]*)"/g

/** Text results in a formula; values compared against answers (`{x} = "yes"`) stay as they are. */
function translateLiterals(formula: string, visit: (text: string) => string) {
  return formula.replace(LITERAL, (whole, inner: string, at: number) => {
    const before = formula.slice(0, at).trimEnd().slice(-1)
    const after = formula.slice(at + whole.length).trimStart().charAt(0)
    const compared = '=<>!'.includes(before || ' ') || '=<>!'.includes(after || ' ')
    return inner && !compared ? `"${visit(inner)}"` : whole
  })
}

interface Visit {
  (text: string): string
}

/** Walks every readable string of a schema; `visit` returns the replacement. */
function walk(schema: FormSchemaV1, visit: Visit) {
  for (const page of schema.pages) {
    if (page.title) page.title = visit(page.title)
    for (const row of page.rows) {
      for (const field of row.fields) {
        if (field.label) field.label = visit(field.label)
        if (field.help) field.help = visit(field.help)
        if (field.placeholder) field.placeholder = visit(field.placeholder)
        for (const option of field.options ?? []) if (option.label) option.label = visit(option.label)
        const props = field.props as Record<string, unknown> | undefined
        if (!props) continue
        for (const name of TEXT_PROPS) if (typeof props[name] === 'string' && props[name]) props[name] = visit(props[name] as string)
        if (Array.isArray(props.rows)) props.rows = props.rows.map(r => (typeof r === 'string' ? visit(r) : r))
        if (typeof props.formula === 'string') props.formula = translateLiterals(props.formula, visit)
      }
    }
  }
  // Text outside the questions: a question's own error message, the help guide's title, the page header subtitle.
  for (const field of schema.pages.flatMap(page => page.rows.flatMap(row => row.fields))) {
    const message = field.validation?.pattern_message
    if (typeof message === 'string' && message) field.validation!.pattern_message = visit(message)
  }
  const guide = schema.settings?.guide
  if (guide?.title) guide.title = visit(guide.title)
  const header = (schema.theme as { header?: { subtitle?: unknown } } | undefined)?.header
  if (header && typeof header.subtitle === 'string' && header.subtitle) header.subtitle = visit(header.subtitle)
  const thanks = schema.thank_you
  if (thanks?.title) thanks.title = visit(thanks.title)
  if (thanks?.message) thanks.message = visit(thanks.message)
}

/** Every readable English string of a template schema (for the message files and their tests). */
export function schemaTexts(schema: FormSchemaV1): string[] {
  const found = new Set<string>()
  walk(structuredClone(schema), text => {
    if (/[a-z]/i.test(text)) found.add(text)
    return text
  })
  return [...found]
}

/** Text compared without capitals or extra spaces. */
const normaliseText = (text: string) => text.trim().replace(/\s+/g, ' ').toLocaleLowerCase()

/**
 * A form's text moved to another language (owner, 2026-10-04: changing a form's language left its
 * questions in English). Works for every text that comes from the template dictionaries — in
 * English, or already in the form's previous language (`from`). Text people wrote themselves has
 * no translation here and stays as it is (`kept`); those are translated per language in M4.
 * `to` / `from` null = English.
 */
export function translateContent(schema: FormSchemaV1, from: Dict | null, to: Dict | null): { schema: FormSchemaV1; translated: number; kept: string[] } {
  // People type "First Name", "first name " or "FIRST NAME": capitals and spacing don't matter.
  const english = new Map(Object.keys(to ?? from ?? {}).map(source => [normaliseText(source), source]))
  const back = new Map(Object.entries(from ?? {}).map(([source, text]) => [normaliseText(text), source]))
  const copy = structuredClone(schema)
  let translated = 0
  const kept = new Set<string>()
  walk(copy, text => {
    const key = normaliseText(text)
    const source = english.get(key) ?? back.get(key)
    const result = source === undefined ? undefined : to ? to[source] : source
    if (result === undefined) {
      if (/\p{L}/u.test(text)) kept.add(text)
      return text
    }
    if (result !== text) translated++
    return result
  })
  return { schema: copy, translated, kept: [...kept] }
}

/** A copy of the schema in another language; `language` is recorded in the form settings. */
export function localiseSchema(schema: FormSchemaV1, dict: Dict | null, language: string): FormSchemaV1 {
  const copy = structuredClone(schema)
  if (dict) walk(copy, text => dict[text] ?? text)
  copy.settings = { ...copy.settings, language: dict ? language : 'en' }
  return copy
}

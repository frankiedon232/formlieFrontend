/**
 * Forms in several languages (F10 M4, decisions 73 and 99). A form has a main language
 * (`settings.language`) and may offer more (`settings.languages`). Every text people read has a
 * stable key (page / field id + what it is), and `schema.translations[lang][key]` holds its
 * translation. Keys, option values, logic and formulas never change, so rules, calculations and
 * answers are the same in every language. A missing translation shows the main language text,
 * never an empty label. Used by the builder (translate), the preview and the public form.
 */
import { APP_LOCALES } from '../i18n/locales'
import type { FormSchemaV1 } from './schema'

/** Short line, longer text (textarea) or rich text (HTML). */
export type TextKind = 'text' | 'long' | 'html'

export interface FormText {
  key: string
  text: string
  kind: TextKind
  /** The page it sits on (null = the whole form: title, guide, thank-you). */
  page: string | null
}

/** Field props that hold readable text, and how long they are. */
const TEXT_PROPS: Record<string, TextKind> = {
  text: 'long',
  html: 'html',
  description: 'long',
  min_label: 'text',
  max_label: 'text',
  link_label: 'text',
  alt: 'text',
  caption: 'text',
}
const LITERAL = /"([^"\\]*)"/g
/** Words to translate: letters, and not a web address or an email example ("https://", "name@example.com"). */
const hasWords = (text: string) => /\p{L}/u.test(text) && !/^\s*([a-z][a-z0-9+.-]*:\/\/\S*|[^\s@]+@[^\s@]+)\s*$/i.test(text)
/** A plain copy (the builder's schema is reactive, which structuredClone can't copy). */
const copyOf = <T>(value: T): T => JSON.parse(JSON.stringify(value)) as T

type Visit = (key: string, text: string, kind: TextKind, page: string | null) => string

/** Text results in a formula ("Pass"); values compared against answers (`{x} = "yes"`) are not text. */
function walkLiterals(formula: string, key: string, page: string, visit: Visit) {
  let n = 0
  return formula.replace(LITERAL, (whole, inner: string, at: number) => {
    const before = formula.slice(0, at).trimEnd().slice(-1)
    const after = formula.slice(at + whole.length).trimStart().charAt(0)
    const compared = '=<>!'.includes(before || ' ') || '=<>!'.includes(after || ' ')
    if (!inner || compared) return whole
    return `"${visit(`${key}.${n++}`, inner, 'text', page)}"`
  })
}

/**
 * Every readable text of a form with its key; `visit` returns the replacement (the schema is
 * changed in place, pass a copy).
 */
export function walkTexts(schema: FormSchemaV1, visit: Visit) {
  /** Swap one text property in place (only when it holds text). */
  const swap = (holder: object | undefined, prop: string, key: string, kind: TextKind, page: string | null) => {
    const target = holder as Record<string, unknown> | undefined
    const text = target?.[prop]
    if (target && typeof text === 'string' && text) target[prop] = visit(key, text, kind, page)
  }
  swap(schema.settings, 'title', 'form.title', 'text', null)
  swap(schema.settings?.guide, 'title', 'guide.title', 'text', null)
  swap(schema.settings?.guide, 'html', 'guide.html', 'html', null)
  swap((schema.theme as { header?: object } | undefined)?.header, 'subtitle', 'header.subtitle', 'text', null)
  for (const page of schema.pages) {
    swap(page, 'title', `page.${page.id}.title`, 'text', page.id)
    for (const field of page.rows.flatMap(row => row.fields)) {
      const at = `field.${field.id}`
      swap(field, 'label', `${at}.label`, 'text', page.id)
      swap(field, 'help', `${at}.help`, 'long', page.id)
      swap(field, 'placeholder', `${at}.placeholder`, 'text', page.id)
      for (const option of field.options ?? []) swap(option, 'label', `${at}.option.${option.value}`, 'text', page.id)
      swap(field.validation, 'pattern_message', `${at}.pattern_message`, 'text', page.id)
      const props = field.props as Record<string, unknown> | undefined
      if (!props) continue
      for (const [name, kind] of Object.entries(TEXT_PROPS)) swap(props, name, `${at}.${name}`, kind, page.id)
      if (Array.isArray(props.rows))
        props.rows = props.rows.map((row, i) => (typeof row === 'string' && row ? visit(`${at}.row.${i}`, row, 'text', page.id) : row))
      if (typeof props.formula === 'string') props.formula = walkLiterals(props.formula, `${at}.formula`, page.id, visit)
    }
  }
  swap(schema.thank_you, 'title', 'thanks.title', 'text', null)
  swap(schema.thank_you, 'message', 'thanks.message', 'long', null)
}

/** Every text people read, in form order (things without letters, like "1" or "→", are left out). */
export function formTexts(schema: FormSchemaV1): FormText[] {
  const found: FormText[] = []
  walkTexts(copyOf(schema), (key, text, kind, page) => {
    if (hasWords(kind === 'html' ? text.replace(/<[^>]*>/g, '') : text)) found.push({ key, text, kind, page })
    return text
  })
  return found
}

const known = (code: string) => APP_LOCALES.some(locale => locale.code === code)

/** The form's main language. */
export const mainLanguage = (schema: FormSchemaV1 | null | undefined) => {
  const main = schema?.settings?.language ?? 'en'
  return known(main) ? main : 'en'
}

/** Languages the form offers: its main language first, then the others. */
export function formLanguages(schema: FormSchemaV1 | null | undefined): string[] {
  const main = mainLanguage(schema)
  return [main, ...new Set((schema?.settings?.languages ?? []).filter(code => code !== main && known(code)))]
}

/** A short fingerprint of a text (FNV-1a), to notice when the original changes after translating. */
export function textHash(text: string): string {
  let hash = 0x811c9dc5
  for (let i = 0; i < text.length; i++) hash = Math.imul(hash ^ text.charCodeAt(i), 0x01000193)
  return (hash >>> 0).toString(36)
}

/** Translations whose original text changed since they were made ("check the translation"). */
export function staleKeys(schema: FormSchemaV1, language: string, texts = formTexts(schema)): Set<string> {
  const saved = schema.translations?.[language] ?? {}
  const from = schema.translated_from?.[language] ?? {}
  return new Set(texts.filter(item => saved[item.key]?.trim() && from[item.key] && from[item.key] !== textHash(item.text)).map(item => item.key))
}

/** How much of a language is done, and how many translations to check. */
export function translationProgress(schema: FormSchemaV1, language: string) {
  const texts = formTexts(schema)
  const saved = schema.translations?.[language] ?? {}
  return { done: texts.filter(item => saved[item.key]?.trim()).length, total: texts.length, stale: staleKeys(schema, language, texts).size }
}

/**
 * The form as respondents see it in one of its languages: every translated text swapped in, the
 * rest in the main language. The main language (or one the form doesn't offer) = the form itself.
 */
export function translateSchema(schema: FormSchemaV1, language: string): FormSchemaV1 {
  if (language === mainLanguage(schema) || !formLanguages(schema).includes(language)) return schema
  const saved = schema.translations?.[language] ?? {}
  const copy = copyOf(schema)
  walkTexts(copy, (key, text) => saved[key]?.trim() || text)
  // No title of its own = the form name; its translation still becomes the title respondents see.
  const title = copy.settings?.title || saved['form.title']?.trim()
  copy.settings = { ...copy.settings, language, ...(title ? { title } : {}) }
  return copy
}

/**
 * Which language a respondent gets (decision 99, owner 2026-10-04): the one in the link (`?lang=`)
 * when the form offers it, else the form's main language (first in `offered`). The browser's
 * language doesn't decide; the switcher on the form is there for that.
 */
export function pickLanguage(offered: string[], wanted: string | null | undefined): string {
  return wanted && offered.includes(wanted) ? wanted : (offered[0] ?? 'en')
}

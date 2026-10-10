/**
 * The mock assistant's translator (F19 M5), built in (no outside service): Formalie's own translations as one
 * dictionary, the portal's interface texts in 20 languages plus the template content and vocabulary. A text it
 * knows (exactly, ignoring case and end punctuation) is translated; anything else is left for a person, never
 * guessed word by word. The backend's model translates the rest.
 */
import { readFileSync } from 'node:fs'
import { join } from 'node:path'
import { translationDict } from '../data/templateStore'

type Dict = Map<string, string>
const cache = new Map<string, Dict>()

function messages(code: string): Record<string, unknown> | null {
  try {
    return JSON.parse(readFileSync(join(process.cwd(), 'i18n', 'locales', `${code}.json`), 'utf8')) as Record<string, unknown>
  } catch {
    return null
  }
}

/** English text → translated text, for every interface string both files have (no placeholders or plurals). */
function interfacePairs(code: string): [string, string][] {
  const en = messages('en')
  const local = messages(code)
  if (!en || !local) return []
  const pairs: [string, string][] = []
  const walk = (a: unknown, b: unknown) => {
    if (typeof a === 'string' && typeof b === 'string') {
      if (a.length >= 2 && a.length <= 160 && !/[{}|@$<]/.test(a) && b.trim() && a !== b) pairs.push([a, b])
      return
    }
    if (a && b && typeof a === 'object' && typeof b === 'object') for (const key of Object.keys(a)) walk((a as Record<string, unknown>)[key], (b as Record<string, unknown>)[key])
  }
  walk(en, local)
  return pairs
}

const norm = (text: string) => text.trim().toLowerCase().replace(/\s+/g, ' ')
const END = /[\s?:.!*]+$/

/** One language's dictionary (cached); template content wins over interface texts. */
function dictFor(code: string): Dict {
  let dict = cache.get(code)
  if (!dict) {
    dict = new Map()
    for (const [en, local] of interfacePairs(code)) if (!dict.has(norm(en))) dict.set(norm(en), local)
    for (const [en, local] of Object.entries(translationDict(code) ?? {})) dict.set(norm(en), local)
    cache.set(code, dict)
  }
  return dict
}

/** Translate one text into `code`, or null when Formalie's dictionaries don't know it. */
export function translatorFor(code: string): (text: string) => string | null {
  const dict = code === 'en' ? null : dictFor(code)
  return text => {
    if (!dict || !text.trim()) return null
    const exact = dict.get(norm(text))
    if (exact) return exact
    // "Email address:" or "Your name?" → the known text with its own ending
    const ending = text.match(END)?.[0] ?? ''
    const core = dict.get(norm(text.replace(END, '')))
    if (core) return `${core.replace(END, '')}${ending.trim()}`
    return null
  }
}


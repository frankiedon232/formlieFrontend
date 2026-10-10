/**
 * Help centre content in the mock (F25): what the Formalie team publishes from the platform admin, shipped as
 * files here (`server/mock/data/help/{lang}.json`, English the source). An article, FAQ or term missing in a
 * language comes in English. Feedback ("Was this helpful?") and searches that found nothing are kept for the
 * Formalie team in `.data/mock/help.json` (the platform admin reads them later).
 */
import { readFileSync } from 'node:fs'
import { join } from 'node:path'
import type { HelpArticleSummary, HelpBlock, HelpCategory, HelpFaq, HelpTerm, HelpTour } from '#shared/types/help'
import { loadPersisted, savePersisted } from '../core/persist'

export interface StoredArticle {
  id: string
  category: HelpCategory
  title: string
  summary: string
  minutes: number
  route: string | null
  related: string[]
  keywords: string[]
  blocks: HelpBlock[]
  /** Order in the "New here?" path. */
  start?: number
  popular?: boolean
}

interface Content {
  articles: StoredArticle[]
  faqs: Omit<HelpFaq, never>[]
  glossary: Omit<HelpTerm, never>[]
  tours?: HelpTour[]
}

/** When the content was last published (the platform admin sets it per article). */
export const HELP_UPDATED_AT = '2026-10-10T09:00:00.000Z'

const files = new Map<string, Content | null>()
function file(lang: string): Content | null {
  if (!files.has(lang)) {
    try {
      files.set(lang, JSON.parse(readFileSync(join(process.cwd(), 'server', 'mock', 'data', 'help', `${lang}.json`), 'utf8')) as Content)
    } catch {
      files.set(lang, null)
    }
  }
  return files.get(lang) ?? null
}

/** The content in a language, item by item falling back to English. */
export function helpContent(lang: string): { articles: (StoredArticle & { language: string })[]; faqs: HelpFaq[]; glossary: HelpTerm[]; tours: HelpTour[] } {
  const en = file('en')!
  const local = lang === 'en' ? null : file(lang)
  const pick = <T extends { id: string }>(list: T[], localList: T[] | undefined) => list.map(item => localList?.find(entry => entry.id === item.id) ?? item)
  return {
    articles: en.articles.map(article => {
      const translated = local?.articles.find(entry => entry.id === article.id)
      // Structure (category, route, related, order) always from the source; the words from the translation
      return translated ? { ...article, title: translated.title, summary: translated.summary, keywords: translated.keywords ?? article.keywords, blocks: translated.blocks, language: lang } : { ...article, language: 'en' }
    }),
    faqs: pick(en.faqs, local?.faqs).map(item => ({ ...item, category: en.faqs.find(entry => entry.id === item.id)!.category, article: en.faqs.find(entry => entry.id === item.id)!.article })),
    glossary: pick(en.glossary, local?.glossary).map(item => ({ ...item, article: en.glossary.find(entry => entry.id === item.id)!.article })),
    // Tours: steps and targets from the source, the words from the translation when there is one
    tours: (en.tours ?? []).map(tour => {
      const translated = local?.tours?.find(entry => entry.id === tour.id)
      return translated ? { ...tour, title: translated.title, steps: tour.steps.map((step, index) => ({ ...step, title: translated.steps[index]?.title ?? step.title, text: translated.steps[index]?.text ?? step.text })) } : tour
    }),
  }
}

export const toSummary = (article: StoredArticle & { language: string }): HelpArticleSummary => ({
  id: article.id,
  category: article.category,
  title: article.title,
  summary: article.summary,
  minutes: article.minutes,
  updated_at: HELP_UPDATED_AT,
  language: article.language,
})

/** The readable text of an article (for search and snippets). */
export const articleText = (article: StoredArticle) =>
  article.blocks
    .map(block => ('text' in block ? block.text : 'items' in block ? block.items.join(' ') : 'label' in block ? block.label : 'caption' in block ? block.caption : ''))
    .join(' ')
    .replace(/\*\*/g, '')

// ── Feedback and searches that found nothing (for the Formalie team) ───────────────────

interface HelpSignals {
  feedback: { article: string; helpful: boolean; comment: string | null; user: string; tenant: string; at: string }[]
  misses: Record<string, { query: string; count: number; last: string }>
}
const signals = loadPersisted<HelpSignals>('help', { feedback: [], misses: {} })
const saveSignals = () => savePersisted('help', () => signals)

export function recordFeedback(entry: HelpSignals['feedback'][number]) {
  signals.feedback = signals.feedback.filter(item => !(item.article === entry.article && item.user === entry.user))
  signals.feedback.push(entry)
  saveSignals()
}
export const feedbackOf = (article: string, user: string) => signals.feedback.find(item => item.article === article && item.user === user)?.helpful ?? null

export function recordMiss(query: string) {
  const key = query.trim().toLowerCase().slice(0, 120)
  if (key.length < 3) return
  const item = signals.misses[key] ?? { query: key, count: 0, last: '' }
  item.count += 1
  item.last = new Date().toISOString()
  signals.misses[key] = item
  saveSignals()
}

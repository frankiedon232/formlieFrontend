/**
 * Mock Help centre (F25, docs/API-CONTRACT.md → Help centre). Read-only content for every signed-in person,
 * in the language asked for (`lang`, English when an item isn't translated yet).
 *
 *   GET  /help/home                    categories with counts, the "New here?" path, popular, recently updated, support
 *   GET  /help/articles?category       summaries
 *   GET  /help/articles/:id            one article with related ones and your "Was this helpful?" answer
 *   POST /help/articles/:id/feedback   { helpful, comment? } (kept for the Formalie team)
 *   GET  /help/search?q                articles (with a snippet), FAQs and glossary terms; nothing found is recorded
 *   GET  /help/faqs?category · /help/glossary
 */
import { z } from 'zod'
import { HELP_CATEGORIES, type HelpArticle, type HelpContext, type HelpHome, type HelpSearchResult } from '#shared/types/help'
import { APP_LOCALES } from '#shared/utils/i18n/locales'
import { requireAuth } from '../core/auth'
import { MockError, ok } from '../core/respond'
import { defineMockRoute } from '../core/route'
import { parseBody } from '../core/validate'
import { articleText, feedbackOf, helpContent, recordFeedback, recordMiss, toSummary } from '../data/helpStore'
import { platformSupport } from '../data/platformStore'

const langOf = (query: Record<string, unknown>) => (typeof query.lang === 'string' && APP_LOCALES.some(locale => locale.code === query.lang) ? query.lang : 'en')

export const helpHome = defineMockRoute(({ event, query }) => {
  requireAuth(event)
  const { articles } = helpContent(langOf(query))
  const home: HelpHome = {
    categories: HELP_CATEGORIES.map(key => ({ key, count: articles.filter(article => article.category === key).length })).filter(item => item.count),
    start: articles.filter(article => article.start).sort((a, b) => a.start! - b.start!).map(toSummary),
    popular: articles.filter(article => article.popular && !article.start).slice(0, 8).map(toSummary),
    updated: articles.slice(-4).reverse().map(toSummary),
    support: platformSupport(),
  }
  return ok(home)
})

export const listHelpArticles = defineMockRoute(({ event, query }) => {
  requireAuth(event)
  const category = typeof query.category === 'string' ? query.category : null
  return ok(helpContent(langOf(query)).articles.filter(article => !category || article.category === category).map(toSummary))
})

export const getHelpArticle = defineMockRoute(({ event, query }) => {
  const { user } = requireAuth(event)
  const { articles } = helpContent(langOf(query))
  const article = articles.find(item => item.id === getRouterParam(event, 'id'))
  if (!article) throw new MockError('FRM-GEN-1004')
  const result: HelpArticle = {
    ...toSummary(article),
    blocks: article.blocks,
    route: article.route,
    related: article.related.map(id => articles.find(item => item.id === id)).filter(item => !!item).map(item => toSummary(item!)),
    helpful: feedbackOf(article.id, user.id),
  }
  return ok(result)
})

export const helpFeedback = defineMockRoute(({ event, body }) => {
  const { user, tenant } = requireAuth(event)
  const id = getRouterParam(event, 'id') ?? ''
  if (!helpContent('en').articles.some(article => article.id === id)) throw new MockError('FRM-GEN-1004')
  const values = parseBody(z.object({ helpful: z.boolean(), comment: z.string().trim().max(1000).nullish() }), body)
  recordFeedback({ article: id, helpful: values.helpful, comment: values.comment || null, user: user.id, tenant: tenant.id, at: new Date().toISOString() })
  return ok({ saved: true })
})

const words = (text: string) => text.toLowerCase().normalize('NFKD').replace(/[̀-ͯ]/g, '').split(/[^\p{L}\p{N}]+/u).filter(word => word.length > 1)

export const searchHelp = defineMockRoute(({ event, query }) => {
  requireAuth(event)
  const q = typeof query.q === 'string' ? query.q.trim().slice(0, 200) : ''
  const lang = langOf(query)
  const content = helpContent(lang)
  // English words find English articles too (the search box isn't always used in the reader's language)
  const english = lang === 'en' ? null : helpContent('en')
  const asked = words(q)
  const score = (fields: [string, number][]) => {
    let total = 0
    for (const [text, weight] of fields) {
      const found = new Set(words(text))
      for (const word of asked) if (found.has(word) || [...found].some(item => item.length > 3 && item.startsWith(word) && word.length > 2)) total += weight
    }
    return total
  }
  const articles = content.articles
    .map(article => {
      const source = english?.articles.find(item => item.id === article.id)
      const text = articleText(article)
      const value = score([[article.title, 6], [article.keywords.join(' '), 4], [article.summary, 3], [text, 1], [source ? `${source.title} ${source.keywords.join(' ')}` : '', 2]])
      const sentence = text.split(/(?<=[.!?])\s+/).find(part => asked.some(word => part.toLowerCase().includes(word))) ?? article.summary
      return { article, value, snippet: sentence.slice(0, 200) }
    })
    .filter(item => item.value > 0)
    .sort((a, b) => b.value - a.value)
    .slice(0, 8)
    .map(item => ({ ...toSummary(item.article), snippet: item.snippet }))
  const faqs = content.faqs.map(item => ({ item, value: score([[item.question, 3], [item.answer, 1]]) })).filter(entry => entry.value > 0).sort((a, b) => b.value - a.value).slice(0, 5).map(entry => entry.item)
  const terms = content.glossary.map(item => ({ item, value: score([[item.term, 4], [item.definition, 1]]) })).filter(entry => entry.value > 0).sort((a, b) => b.value - a.value).slice(0, 4).map(entry => entry.item)
  if (q && !articles.length && !faqs.length && !terms.length) recordMiss(q)
  const result: HelpSearchResult = { query: q, articles, faqs, terms, answer: answerFor(q, asked, articles[0]?.id, content.articles) }
  return ok(result)
})

/** Patterns like /forms/:id/build match any form's page. */
const matches = (pattern: string, path: string) => new RegExp(`^${pattern.replace(/:[a-z]+/g, '[^/]+')}/?$`).test(path)

/** GET /help/context?path: the article for the page someone is on, more for it, and its tour. */
export const helpContext = defineMockRoute(({ event, query }) => {
  const { user } = requireAuth(event)
  const path = typeof query.path === 'string' ? query.path.split('?')[0]! : '/'
  const { articles, tours } = helpContent(langOf(query))
  // The page's own articles; Getting started ones only when nothing else explains it
  const found = articles.filter(article => article.route && matches(article.route, path)).sort((a, b) => Number(a.category === 'start') - Number(b.category === 'start') || Number(!!b.popular) - Number(!!a.popular))
  const main = found[0]
  const context: HelpContext = {
    article: main
      ? { ...toSummary(main), blocks: main.blocks, route: main.route, related: main.related.map(id => articles.find(item => item.id === id)).filter(item => !!item).map(item => toSummary(item!)), helpful: feedbackOf(main.id, user.id) }
      : null,
    more: found.slice(1, 5).map(toSummary),
    tour: tours.find(tour => matches(tour.route, path)) ?? null,
  }
  return ok(context)
})

/**
 * The answer the assistant gives from the knowledge base (F25 M4): the best article's steps for a "how" question,
 * else its paragraph that matches the question best and what follows it. The backend's model writes a real
 * answer from the same articles; it always names the article it came from.
 */
function answerFor(q: string, asked: string[], id: string | undefined, articles: ReturnType<typeof helpContent>['articles']): HelpSearchResult['answer'] {
  const article = articles.find(item => item.id === id)
  if (!article || asked.length < 1) return null
  const how = /\b(how|where|steps?|create|add|make|set|change|wie|comment|cómo|como|come|hoe|jak|как|як)\b/i.test(q)
  const steps = article.blocks.find(block => block.type === 'steps')
  if (how && steps) return { article: toSummary(article), blocks: [steps] }
  const scored = article.blocks
    .map((block, index) => ({ index, value: 'text' in block ? asked.filter(word => block.text.toLowerCase().includes(word)).length : 0 }))
    .filter(item => item.value > 0)
    .sort((a, b) => b.value - a.value)[0]
  const at = scored?.index ?? article.blocks.findIndex(block => block.type === 'p')
  if (at < 0) return null
  return { article: toSummary(article), blocks: article.blocks.slice(at, at + 2).filter(block => block.type !== 'h' && block.type !== 'show' && block.type !== 'media') }
}

export const listHelpFaqs = defineMockRoute(({ event, query }) => {
  requireAuth(event)
  const category = typeof query.category === 'string' ? query.category : null
  return ok(helpContent(langOf(query)).faqs.filter(item => !category || item.category === category))
})

export const listHelpGlossary = defineMockRoute(({ event, query }) => {
  requireAuth(event)
  return ok([...helpContent(langOf(query)).glossary].sort((a, b) => a.term.localeCompare(b.term, langOf(query))))
})

import { existsSync, readdirSync, readFileSync, statSync } from 'node:fs'
import { join } from 'node:path'
import { describe, expect, it } from 'vitest'
import { HELP_CATEGORIES } from '../../shared/types/help'
import { APP_LOCALES } from '../../shared/utils/i18n/locales'

const read = (lang: string) => JSON.parse(readFileSync(join('server', 'mock', 'data', 'help', `${lang}.json`), 'utf8'))
const en = read('en')

/** Every data-help="…" marker in the app's components and pages. */
function markers(dir: string, found = new Set<string>()): Set<string> {
  for (const name of readdirSync(dir)) {
    const path = join(dir, name)
    if (statSync(path).isDirectory()) markers(path, found)
    else if (name.endsWith('.vue')) for (const match of readFileSync(path, 'utf8').matchAll(/data-help="([a-z-]+)"/g)) found.add(match[1]!)
  }
  return found
}
const pageExists = (route: string) => {
  const base = join('app', 'pages', ...route.replace(/:id/g, '[id]').split('/').filter(Boolean))
  return existsSync(`${base}.vue`) || existsSync(join(base, 'index.vue'))
}

describe('help centre content', () => {
  it('has unique ids, known areas and working links between articles', () => {
    const ids = en.articles.map((article: { id: string }) => article.id)
    expect(new Set(ids).size).toBe(ids.length)
    for (const article of en.articles) {
      expect(HELP_CATEGORIES).toContain(article.category)
      for (const id of article.related) expect(ids).toContain(id)
    }
    for (const item of [...en.faqs, ...en.glossary]) if (item.article) expect(ids).toContain(item.article)
  })

  it('points only at pages that exist and controls that are marked', () => {
    const marked = markers('app')
    for (const article of en.articles) {
      if (article.route) expect(pageExists(article.route), article.route).toBe(true)
      for (const block of article.blocks) {
        if (block.type !== 'show') continue
        expect(pageExists(block.to), block.to).toBe(true)
        if (block.target) expect(marked.has(block.target), block.target).toBe(true)
      }
    }
    for (const tour of en.tours) for (const step of tour.steps) expect(marked.has(step.target), step.target).toBe(true)
  })

  it('has the same structure in every translated language', () => {
    for (const { code } of APP_LOCALES) {
      if (code === 'en' || !existsSync(join('server', 'mock', 'data', 'help', `${code}.json`))) continue
      const local = read(code)
      expect(local.articles.map((article: { id: string }) => article.id), code).toEqual(en.articles.map((article: { id: string }) => article.id))
      local.articles.forEach((article: { blocks: { type: string }[] }, index: number) => expect(article.blocks.map(block => block.type), `${code} ${index}`).toEqual(en.articles[index].blocks.map((block: { type: string }) => block.type)))
      expect(local.faqs.length, code).toBe(en.faqs.length)
      expect(local.glossary.length, code).toBe(en.glossary.length)
    }
  })
})

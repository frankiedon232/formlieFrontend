// Copies formlyBackend's legal drafts (docs/legal/*.md) into app/data/legal.json, in the same shape as
// GET /public/legal/{slug} (docs/LEGAL-PAGES.md), so the site has the real text when the API doesn't answer.
// The website never invents legal wording: run this again whenever the backend's drafts change.
//   pnpm legal:sync            (reads ../formlyBackend/docs/legal)
//   pnpm legal:sync <folder>   (another folder)
import { readFileSync, writeFileSync } from 'node:fs'
import { join } from 'node:path'

const root = join(import.meta.dirname, '..')
const source = process.argv[2] ?? join(root, '../formlyBackend/docs/legal')
const SLUGS = ['privacy', 'terms', 'data-protection', 'cookies', 'acceptable-use', 'subprocessors', 'refunds']

function parse(slug) {
  const text = readFileSync(join(source, `${slug}.md`), 'utf8').replace(/\r\n/g, '\n')
  const match = text.match(/^---\n([\s\S]*?)\n---\n([\s\S]*)$/)
  if (!match) throw new Error(`${slug}.md has no front matter`)
  const meta = Object.fromEntries(
    match[1].split('\n').map(line => {
      const at = line.indexOf(':')
      return [
        line.slice(0, at).trim(),
        line
          .slice(at + 1)
          .trim()
          .replace(/^"(.*)"$/, '$1'),
      ]
    }),
  )
  const sections = []
  for (const part of match[2].split(/^## /m).slice(1)) {
    const [first, ...rest] = part.split('\n')
    const heading = first.match(/^(.*?)\s*\{#([\w-]+)\}\s*$/)
    if (!heading) throw new Error(`${slug}.md: a section heading has no {#id}: ${first}`)
    sections.push({ id: heading[2], heading: heading[1], body_markdown: `${rest.join('\n').trim()}\n` })
  }
  const updated = /^\d{4}-\d{2}-\d{2}/.test(meta.updated_at ?? '') ? meta.updated_at : null
  return {
    slug,
    title: meta.title,
    version: Number(meta.version) || 1,
    updated_at: updated,
    summary_of_changes: meta.summary_of_changes ?? null,
    language: 'en',
    status: 'draft',
    sections,
  }
}

const documents = SLUGS.map(parse)
writeFileSync(
  join(root, 'app/data/legal.json'),
  `${JSON.stringify({ _note: 'Copied from formlyBackend docs/legal by pnpm legal:sync. Fallback only: the live text comes from GET /public/legal.', documents }, null, 2)}\n`,
)
console.log(documents.map(doc => `${doc.slug}: ${doc.sections.length} sections`).join('\n'))

/**
 * Legal documents (docs/LEGAL-PAGES.md): the shape of GET /public/legal/{slug}, checked before use, the order of the
 * legal navigation, and the copy of formlyBackend's drafts kept for when the API doesn't answer
 * (app/data/legal.json, `pnpm legal:sync`). Pure, so it is unit-tested.
 */
import { z } from 'zod'
import fallback from '~/data/legal.json'

/** The legal documents in navigation order; refunds is the seventh, after subprocessors (owner, 2026-10-13). */
export const LEGAL_SLUGS = [
  'privacy',
  'terms',
  'data-protection',
  'cookies',
  'acceptable-use',
  'subprocessors',
  'refunds',
] as const
export type LegalSlug = (typeof LEGAL_SLUGS)[number]

/** The i18n key of each document's name (`legal.{key}`). */
export const LEGAL_KEYS: Record<LegalSlug, string> = {
  privacy: 'privacy',
  terms: 'terms',
  'data-protection': 'dataProtection',
  cookies: 'cookies',
  'acceptable-use': 'acceptableUse',
  subprocessors: 'subprocessors',
  refunds: 'refunds',
}

/** One icon per document, the same in the navigator and the hero. */
export const LEGAL_ICONS: Record<LegalSlug, string> = {
  privacy: 'i-lucide-eye-off',
  terms: 'i-lucide-file-text',
  'data-protection': 'i-lucide-file-lock',
  cookies: 'i-lucide-cookie',
  'acceptable-use': 'i-lucide-scale',
  subprocessors: 'i-lucide-network',
  refunds: 'i-lucide-receipt',
}

/** Minutes to read a document (about 220 words a minute), at least one. */
export function readingMinutes(document: { sections: { body_markdown: string }[] }): number {
  const words = document.sections.reduce(
    (total, section) => total + section.body_markdown.split(/\s+/).filter(Boolean).length,
    0,
  )
  return Math.max(1, Math.round(words / 220))
}

/** "3. Who we are" → { number: '03', title: 'Who we are' }; headings without a number keep their text. */
export function splitHeading(heading: string): { number: string | null; title: string } {
  const match = heading.match(/^(\d+)\.\s*(.+)$/)
  return match ? { number: match[1]!.padStart(2, '0'), title: match[2]! } : { number: null, title: heading }
}

const documentSchema = z.object({
  slug: z.string(),
  title: z.string(),
  version: z.number(),
  updated_at: z.string().nullable(),
  summary_of_changes: z.string().nullable().optional(),
  language: z.string().default('en'),
  status: z.enum(['published', 'draft']).default('draft'),
  sections: z.array(z.object({ id: z.string(), heading: z.string(), body_markdown: z.string() })).min(1),
})

export type LegalDocument = z.infer<typeof documentSchema>
export type LegalSource = 'api' | 'fallback'

export const isLegalSlug = (slug: string): slug is LegalSlug =>
  (LEGAL_SLUGS as readonly string[]).includes(slug)

/** Checks an API answer (`{ success, data }`); null when it isn't a usable document. */
export function parseLegal(answer: unknown): LegalDocument | null {
  const envelope = z.object({ success: z.literal(true), data: documentSchema }).safeParse(answer)
  return envelope.success ? envelope.data.data : null
}

/** The copy of the backend's drafts, always in English. */
export function fallbackLegal(slug: LegalSlug): LegalDocument {
  const document = fallback.documents.find(item => item.slug === slug)
  return documentSchema.parse(document)
}

/** Every section of every document whose heading or text contains the query (the navigator's search). */
export function searchLegal(query: string, documents: LegalDocument[] = LEGAL_SLUGS.map(fallbackLegal)) {
  const needle = query.trim().toLocaleLowerCase()
  if (needle.length < 2) return []
  return documents.flatMap(document =>
    document.sections
      .filter(section => `${section.heading} ${section.body_markdown}`.toLocaleLowerCase().includes(needle))
      .map(section => ({
        slug: document.slug,
        id: section.id,
        heading: section.heading,
        title: document.title,
      })),
  )
}

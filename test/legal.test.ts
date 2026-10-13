import { describe, expect, it } from 'vitest'
import {
  fallbackLegal,
  isLegalSlug,
  LEGAL_SLUGS,
  parseLegal,
  readingMinutes,
  searchLegal,
  splitHeading,
} from '../app/utils/legal'

describe('legal documents (docs/LEGAL-PAGES.md)', () => {
  it('has seven documents, refunds after subprocessors', () => {
    expect(LEGAL_SLUGS).toHaveLength(7)
    expect(LEGAL_SLUGS.indexOf('refunds')).toBe(LEGAL_SLUGS.indexOf('subprocessors') + 1)
    expect(isLegalSlug('privacy')).toBe(true)
    expect(isLegalSlug('nope')).toBe(false)
  })

  it('keeps a full copy of every draft with stable section anchors', () => {
    for (const slug of LEGAL_SLUGS) {
      const document = fallbackLegal(slug)
      expect(document.slug).toBe(slug)
      expect(document.status).toBe('draft')
      expect(document.sections.length).toBeGreaterThan(3)
      expect(document.sections.every(section => /^[a-z0-9-]+$/.test(section.id))).toBe(true)
    }
    expect(fallbackLegal('privacy').sections.map(section => section.id)).toContain('retention')
  })

  it('accepts the API shape and refuses anything else', () => {
    const data = fallbackLegal('terms')
    expect(parseLegal({ success: true, data, meta: {} })?.sections).toHaveLength(data.sections.length)
    expect(parseLegal({ success: true, data: { ...data, sections: [] } })).toBeNull()
    expect(parseLegal({ success: false, error: { code: 'FRM-GEN-1004' } })).toBeNull()
  })

  it('searches headings and text across documents', () => {
    const hits = searchLegal('paddle')
    expect(hits.length).toBeGreaterThan(0)
    expect(hits.some(hit => hit.slug === 'refunds')).toBe(true)
    expect(searchLegal('a')).toEqual([])
  })

  it('splits numbered headings and estimates reading time', () => {
    expect(splitHeading('3. What we collect')).toEqual({ number: '03', title: 'What we collect' })
    expect(splitHeading('12. Contact')).toEqual({ number: '12', title: 'Contact' })
    expect(splitHeading('Contact')).toEqual({ number: null, title: 'Contact' })
    expect(readingMinutes(fallbackLegal('terms'))).toBeGreaterThan(1)
    expect(readingMinutes({ sections: [{ body_markdown: 'short' }] })).toBe(1)
  })
})

import { defineCollection, defineContentConfig } from '@nuxt/content'
import { z } from 'zod'

// Long copy kept in the repository (docs/01-ARCHITECTURE.md): the blog, the changelog, and the legal pages'
// fallback copy for when the backend API doesn't answer (docs/LEGAL-PAGES.md).
export default defineContentConfig({
  collections: {
    blog: defineCollection({
      type: 'page',
      source: 'blog/*.md',
      schema: z.object({
        date: z.string(),
        image: z.string().optional(),
      }),
    }),
    changelog: defineCollection({
      type: 'page',
      source: 'changelog/*.md',
      schema: z.object({
        date: z.string(),
        version: z.string().optional(),
      }),
    }),
    legal: defineCollection({
      type: 'page',
      source: 'legal/*.md',
      schema: z.object({
        slug: z.string(),
        version: z.number(),
        updated_at: z.string().nullable(),
        summary_of_changes: z.string().optional(),
      }),
    }),
  },
})

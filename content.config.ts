import { defineCollection, defineContentConfig } from '@nuxt/content'
import { z } from 'zod'

// Long copy kept in the repository (docs/01-ARCHITECTURE.md): the blog and the changelog. The legal pages' fallback
// copy is app/data/legal.json (pnpm legal:sync), in the API's own shape.
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
  },
})

import { defineConfig } from 'vitest/config'

// Pure unit tests (links, locales, data). Component tests with @nuxt/test-utils come with the pages.
export default defineConfig({
  test: {
    include: ['test/**/*.test.ts'],
    environment: 'node',
  },
})

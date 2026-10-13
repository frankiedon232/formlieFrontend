import { fileURLToPath } from 'node:url'
import { defineConfig } from 'vitest/config'

// Pure unit tests (links, locales, data). Component tests with @nuxt/test-utils come with the pages.
export default defineConfig({
  resolve: {
    alias: { '~': fileURLToPath(new URL('./app', import.meta.url)) },
  },
  test: {
    include: ['test/**/*.test.ts'],
    environment: 'node',
  },
})

import { fileURLToPath } from 'node:url'
import { defineConfig } from 'vitest/config'

// Pure unit tests (crypto, api client, utils). Component tests via @nuxt/test-utils come later.
export default defineConfig({
  resolve: {
    alias: {
      '#shared': fileURLToPath(new URL('./shared', import.meta.url)),
    },
  },
  test: {
    include: ['test/**/*.test.ts'],
    environment: 'node',
  },
})

import { defineConfig } from 'vitest/config'

// Pure unit tests (crypto, utils). Component tests via @nuxt/test-utils come later.
export default defineConfig({
  test: {
    include: ['test/**/*.test.ts'],
    environment: 'node',
  },
})

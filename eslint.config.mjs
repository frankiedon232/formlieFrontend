// @ts-check
import withNuxt from './.nuxt/eslint.config.mjs'

export default withNuxt({
  rules: {
    // Rule 2 (CLAUDE.md): components/composables are auto-imported, never imported by path.
    'no-restricted-imports': [
      'error',
      {
        patterns: [
          { group: ['*.vue'], message: 'Components are auto-imported, use <PrefixName /> instead.' },
          {
            group: ['~/composables/*', '~/composables/**', '@/composables/**'],
            message: 'Composables are auto-imported.',
          },
        ],
      },
    ],
    'vue/multi-word-component-names': 'off',
  },
})

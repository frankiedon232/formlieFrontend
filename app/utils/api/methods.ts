/**
 * Colours of the HTTP methods (owner, 2026-10-06: endpoints and their methods told apart at a
 * glance), only from the theme: GET green (reads), POST violet (adds), PUT amber (changes), DELETE red
 * (removes). Text one shade deeper than Nuxt UI's subtle default, like the status badges.
 */
import type { BadgeProps } from '@nuxt/ui'
import type { ApiMethod } from '#shared/utils/urls/public'

export const METHOD_COLOR: Record<ApiMethod, BadgeProps['color']> = { GET: 'success', POST: 'secondary', PUT: 'warning', DELETE: 'error' }
export const METHOD_TEXT: Record<ApiMethod, string> = {
  GET: 'text-(--ui-color-success-700) dark:text-(--ui-color-success-300)',
  POST: 'text-(--ui-color-secondary-700) dark:text-(--ui-color-secondary-300)',
  PUT: 'text-(--ui-color-warning-700) dark:text-(--ui-color-warning-300)',
  DELETE: 'text-(--ui-color-error-700) dark:text-(--ui-color-error-300)',
}
/** A thin coloured mark for method rows (start border). */
export const METHOD_BAR: Record<ApiMethod, string> = { GET: 'bg-success', POST: 'bg-secondary', PUT: 'bg-warning', DELETE: 'bg-error' }

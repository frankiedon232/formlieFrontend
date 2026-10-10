/** Help centre areas (F25): the icon each shows with (names and descriptions are translated: help.category.<key>). */
import type { HelpCategory } from '../../types/help'

export const HELP_CATEGORY_ICONS: Record<HelpCategory, string> = {
  start: 'i-lucide-rocket',
  forms: 'i-lucide-file-text',
  builder: 'i-lucide-layout-panel-top',
  design: 'i-lucide-palette',
  templates: 'i-lucide-layout-template',
  sharing: 'i-lucide-share-2',
  responses: 'i-lucide-inbox',
  analytics: 'i-lucide-chart-line',
  lists: 'i-lucide-list',
  data: 'i-lucide-database',
  api: 'i-lucide-boxes',
  people: 'i-lucide-users',
  settings: 'i-lucide-settings',
  audit: 'i-lucide-scroll-text',
  ai: 'i-lucide-sparkles',
}

/** An article's address in the portal: /help/{area}/{article}. */
export const helpArticlePath = (article: { id: string; category: HelpCategory }) => `/help/${article.category}/${article.id}`

/**
 * AI assistant kinds (F19): the icon, the credits a request costs, the permission it needs and the page it
 * belongs to. Shared by the app and the mock so both count and show requests the same way.
 */
import type { AiKind } from '../../types/ai'
import type { Permission } from '../auth/permissions'

export const AI_KIND_META: Record<AiKind, { icon: string; credits: number; permission: Permission; page: string }> = {
  form: { icon: 'i-lucide-file-plus-2', credits: 5, permission: 'ai.create', page: '/ai/create-form' },
  template: { icon: 'i-lucide-layout-template', credits: 5, permission: 'ai.create', page: '/ai/templates' },
  theme: { icon: 'i-lucide-palette', credits: 2, permission: 'ai.create', page: '/ai/templates' },
  builder: { icon: 'i-lucide-wand-sparkles', credits: 2, permission: 'ai.assist', page: '/ai' },
  analysis: { icon: 'i-lucide-chart-scatter', credits: 8, permission: 'ai.analyse', page: '/ai/analysis' },
  question: { icon: 'i-lucide-message-circle-question', credits: 3, permission: 'ai.analyse', page: '/ai/analysis' },
  summary: { icon: 'i-lucide-lightbulb', credits: 3, permission: 'ai.analyse', page: '/ai/insights' },
  translate: { icon: 'i-lucide-languages', credits: 4, permission: 'ai.translate', page: '/ai/translate' },
  rewrite: { icon: 'i-lucide-pen-line', credits: 1, permission: 'ai.translate', page: '/ai/translate' },
}

/** The monthly allowance until plans arrive (F24). */
export const AI_DEFAULT_MONTHLY_CREDITS = 500

import type { NavCounts } from '#shared/types/navigation'
import { SYSTEM_TEMPLATES, TEMPLATE_CATEGORY_KEYS } from '#shared/templates'
import { requireAuth } from '../core/auth'
import { ok } from '../core/respond'
import { defineMockRoute } from '../core/route'
import { formsOf } from '../data/formStore'
import { canSee } from '../data/formPermissions'
import { formResponses } from '../data/responseData'
import { libraryOf } from '../data/libraryStore'
import { allTemplates } from '../data/templateStore'
import { SYSTEM_THEME_COUNT } from './themes'

/** GET /navigation/counts, cheap counters and short lists for the sidebar. */
export const navigationCounts = defineMockRoute(({ event }) => {
  const { tenant, user } = requireAuth(event)
  // People access: forms someone may not see aren't counted for them either.
  const all = formsOf(tenant).forms.filter(form => canSee(form, user))
  const live = all.filter(form => !form.deleted_at)
  const count = (status: string) => live.filter(form => form.status === status).length

  // Responses by review status, from the response data (decision 100): what the Responses pages show.
  const byStatus = { new: 0, reviewed: 0, approved: 0, rejected: 0 }
  for (const form of live) for (const entry of formResponses(tenant, form)) byStatus[entry.status]++
  const total = byStatus.new + byStatus.reviewed + byStatus.approved + byStatus.rejected

  // Templates: Formalie's categories, most used first (forms made from them), then the largest.
  const templates = allTemplates(tenant, 'en')
  const system = templates.filter(item => item.source === 'system')
  const categories = TEMPLATE_CATEGORY_KEYS.map(key => {
    const inside = system.filter(item => item.category === key)
    return { key, count: inside.length, forms: inside.reduce((sum, item) => sum + item.forms_count, 0) }
  })
    .filter(item => item.count > 0)
    .sort((a, b) => b.forms - a.forms || b.count - a.count)
    .map(({ key, count }) => ({ key, count }))
  const themes = [...(libraryOf(tenant).themes ?? [])].sort((a, b) => b.updated_at.localeCompare(a.updated_at))

  return ok<NavCounts>({
    forms: {
      all: live.filter(form => form.status !== 'archived').length,
      draft: count('draft'),
      published: count('published'),
      closed: count('closed'),
      archived: count('archived'),
      trash: all.length - live.length,
    },
    responses: { all: total, ...byStatus },
    templates: { total: system.length || SYSTEM_TEMPLATES.length, mine: templates.length - system.length, categories },
    themes: {
      total: themes.length + SYSTEM_THEME_COUNT,
      system: SYSTEM_THEME_COUNT,
      saved: themes.filter(theme => (theme.source ?? 'saved') === 'saved').length,
      created: themes.filter(theme => theme.source === 'created').length,
    },
  })
})

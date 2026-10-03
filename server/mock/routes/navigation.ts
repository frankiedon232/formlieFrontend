import type { NavCounts } from '#shared/types/navigation'
import { SYSTEM_TEMPLATES } from '#shared/templates'
import { requireAuth } from '../core/auth'
import { ok } from '../core/respond'
import { defineMockRoute } from '../core/route'
import { formsOf } from '../data/formStore'
import { libraryOf } from '../data/libraryStore'
import { allTemplates } from '../data/templateStore'
import { SYSTEM_THEME_COUNT } from './themes'

/** GET /navigation/counts — cheap counters and short lists for the sidebar. */
export const navigationCounts = defineMockRoute(({ event }) => {
  const { tenant } = requireAuth(event)
  const all = formsOf(tenant).forms
  const live = all.filter(form => !form.deleted_at)
  const count = (status: string) => live.filter(form => form.status === status).length

  // Mock: responses split by review status (a small share of published forms' responses is unread).
  const total = live.reduce((sum, form) => sum + form.responses_count, 0)
  const unread = live.filter(form => form.status === 'published').reduce((sum, form) => sum + Math.floor(form.responses_count / 400), 0)
  const reviewed = Math.round((total - unread) * 0.22)
  const rejected = Math.round((total - unread) * 0.06)

  // Templates: last used first (forms made from them), then the most used, then the catalogue order.
  const templates = allTemplates(tenant, 'en')
  const recent = [...templates]
    .sort((a, b) => (b.last_used_at ?? '').localeCompare(a.last_used_at ?? '') || b.forms_count - a.forms_count)
    .slice(0, 6)
    .map(item => ({ key: item.key, name: item.name }))
  const themes = [...(libraryOf(tenant).themes ?? [])].sort((a, b) => b.updated_at.localeCompare(a.updated_at))

  return ok<NavCounts>({
    forms: {
      all: live.filter(form => form.status !== 'archived').length,
      draft: count('draft'),
      published: count('published'),
      closed: count('closed'),
      trash: all.length - live.length,
    },
    responses: { all: total, new: unread, reviewed, approved: total - unread - reviewed - rejected, rejected },
    templates: { total: templates.length || SYSTEM_TEMPLATES.length, recent },
    themes: { total: themes.length + SYSTEM_THEME_COUNT, recent: themes.slice(0, 6).map(theme => ({ id: theme.id, name: theme.name })) },
  })
})

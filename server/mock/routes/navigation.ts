import type { NavCounts } from '#shared/types/navigation'
import { requireAuth } from '../core/auth'
import { ok } from '../core/respond'
import { defineMockRoute } from '../core/route'
import { formsOf } from '../data/formStore'

/** GET /navigation/counts — cheap counters for the sidebar badges. */
export const navigationCounts = defineMockRoute(({ event }) => {
  const { tenant } = requireAuth(event)
  const all = formsOf(tenant).forms
  const live = all.filter(form => !form.deleted_at)
  const count = (status: string) => live.filter(form => form.status === status).length
  return ok<NavCounts>({
    forms: {
      all: live.filter(form => form.status !== 'archived').length,
      draft: count('draft'),
      published: count('published'),
      closed: count('closed'),
      trash: all.length - live.length,
    },
    // Mock: a small share of each live form's responses is still unread.
    responses: {
      new: live
        .filter(form => form.status === 'published')
        .reduce((sum, form) => sum + Math.floor(form.responses_count / 400), 0),
    },
  })
})

import type { NavCounts } from '#shared/types/navigation'
import { requireAuth } from '../core/auth'
import { ok } from '../core/respond'
import { defineMockRoute } from '../core/route'
import { MOCK_FORMS } from '../data/forms'

/** GET /navigation/counts — cheap counters for the sidebar badges. */
export const navigationCounts = defineMockRoute(({ event }) => {
  requireAuth(event)
  const count = (status: string) => MOCK_FORMS.filter(form => form.status === status).length
  return ok<NavCounts>({
    forms: {
      all: MOCK_FORMS.filter(form => form.status !== 'archived').length,
      draft: count('draft'),
      published: count('published'),
      closed: count('closed'),
    },
    // Mock: a small share of each live form's responses is still unread.
    responses: {
      new: MOCK_FORMS.filter(form => form.status === 'published').reduce(
        (sum, form) => sum + Math.floor(form.responses_count / 400),
        0,
      ),
    },
  })
})

/**
 * Dashboard, Forms view (F21 M2, docs/API-CONTRACT.md → Dashboard): running the forms, next to Analytics (which
 * analyses them). Forms the person may see (role, sharing, folder access); responses only of forms whose
 * responses they may see.
 *
 *   GET /dashboard/forms?from&to&group → FormsDashboard
 */
import type { FormsDashboard } from '#shared/types/dashboard'
import { bucketStart } from '#shared/utils/dashboard/buckets'
import { requireAuth } from '../core/auth'
import { ok } from '../core/respond'
import { defineMockRoute } from '../core/route'
import { canSee, responsesAllowed } from '../data/formPermissions'
import { formsOf } from '../data/formStore'
import { formResponses } from '../data/responseData'
import { periodFrom } from './dashboard'

const DAY = 86_400_000
const iso = (time: number) => new Date(time).toISOString().slice(0, 10)
type Work = FormsDashboard['work'][number]

export const formsDashboard = defineMockRoute(({ event, query }) => {
  const { tenant, user } = requireAuth(event)
  const { from, to, group, prevFrom, end, buckets } = periodFrom(query)
  const index = new Map(buckets.map((start, i) => [start, i]))
  const forms = formsOf(tenant).forms.filter(form => !form.deleted_at && canSee(form, user))
  const now = Date.now()

  const created = buckets.map(start => ({ start, count: 0 }))
  let createdNow = 0
  let createdBefore = 0
  const channels = { link: 0, embed: 0, api: 0 }
  const top: FormsDashboard['top'] = []
  const folders = new Map<string, FormsDashboard['folders'][number]>()
  const owners = new Map<string, FormsDashboard['owners'][number]>()
  const work: Work[] = []
  let silent = 0
  let active = 0
  let activeBefore = 0
  let responsesNow = 0
  let responsesBefore = 0

  for (const form of forms) {
    const made = Date.parse(form.created_at)
    if (made >= from && made <= end) {
      createdNow++
      const i = index.get(iso(bucketStart(made, group)))
      if (i !== undefined) created[i]!.count++
    } else if (made >= prevFrom && made < from) createdBefore++

    let own = 0
    let ownBefore = 0
    if (responsesAllowed(form, user, 'view', tenant))
      for (const entry of formResponses(tenant, form)) {
        if (entry.at >= from && entry.at <= end) {
          own++
          channels[entry.channel]++
        } else if (entry.at >= prevFrom && entry.at < from) ownBefore++
      }
    responsesNow += own
    responsesBefore += ownBefore
    if (own) active++
    if (ownBefore) activeBefore++
    if (own || ownBefore) top.push({ id: form.id, name: form.name, status: form.status, responses: own, previous: ownBefore, completion_rate: form.completion_rate || 0 })

    const folderKey = form.folder?.id ?? '_none'
    const folder = folders.get(folderKey) ?? { id: form.folder?.id ?? null, name: form.folder?.name ?? null, forms: 0, responses: 0 }
    folder.forms++
    folder.responses += own
    folders.set(folderKey, folder)
    const owner = owners.get(form.owner.id) ?? { id: form.owner.id, name: form.owner.name, forms: 0, responses: 0 }
    owner.forms++
    owner.responses += own
    owners.set(form.owner.id, owner)

    // What needs work
    const ref = { id: form.id, name: form.name }
    if (form.status === 'draft' && now - Date.parse(form.updated_at) > 14 * DAY) work.push({ kind: 'stale_draft', form: ref, at: form.updated_at, count: null })
    if (form.status === 'published' && !own) {
      silent++
      work.push({ kind: 'no_responses', form: ref, at: null, count: null })
    }
    if (form.has_unpublished_changes) work.push({ kind: 'unpublished_changes', form: ref, at: form.updated_at, count: null })
    if (form.status === 'published' && form.closes_at && Date.parse(form.closes_at) > now && Date.parse(form.closes_at) < now + 7 * DAY) work.push({ kind: 'closing', form: ref, at: form.closes_at, count: null })
    if (form.status === 'published' && form.response_limit && form.responses_count >= form.response_limit * 0.9) work.push({ kind: 'nearly_full', form: ref, at: null, count: form.response_limit })
  }

  const ORDER: Record<Work['kind'], number> = { nearly_full: 0, closing: 1, no_responses: 2, unpublished_changes: 3, stale_draft: 4 }
  work.sort((a, b) => ORDER[a.kind] - ORDER[b.kind])
  const byStatus = (status: string) => forms.filter(form => form.status === status).length
  const perForm = (responses: number, count: number) => (count ? Math.round(responses / count) : 0)
  const result: FormsDashboard = {
    from: iso(from),
    to: iso(to),
    group,
    kpis: {
      published: { value: byStatus('published'), previous: null },
      created: { value: createdNow, previous: createdBefore },
      per_form: { value: perForm(responsesNow, active), previous: activeBefore ? perForm(responsesBefore, activeBefore) : null },
      silent: { value: silent, previous: null },
      unpublished: { value: forms.filter(form => form.has_unpublished_changes).length, previous: null },
    },
    by_status: { draft: byStatus('draft'), published: byStatus('published'), closed: byStatus('closed'), archived: byStatus('archived') },
    created,
    channels,
    top: top.sort((a, b) => b.responses - a.responses).slice(0, 8),
    folders: [...folders.values()].sort((a, b) => b.responses - a.responses || b.forms - a.forms).slice(0, 8),
    owners: [...owners.values()].sort((a, b) => b.responses - a.responses || b.forms - a.forms).slice(0, 6),
    work: work.slice(0, 12),
  }
  return ok(result)
})

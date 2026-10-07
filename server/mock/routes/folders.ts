/**
 * Mock folder pages (F11 M4, owner request 2026-10-02: folder pages and an all-folders view with
 * statistics). Each folder with its numbers, counted only over forms this person may see (people
 * access): forms by status, responses all time and in the last 30 days (day by day, and the 30
 * days before for the change), average completion of its published forms, last activity, owners.
 */
import type { FolderRow, FormFolder } from '#shared/types/forms'
import { requireAuth } from '../core/auth'
import { MockError, ok, paginate } from '../core/respond'
import { defineMockRoute } from '../core/route'
import { canSee } from '../data/formPermissions'
import { formsOf, type StoredForm } from '../data/formStore'
import { formResponses } from '../data/responseData'
import type { MockTenant, MockUser } from '../data/tenants'

const DAY = 86_400_000

function rowOf(tenant: MockTenant, folder: FormFolder, forms: StoredForm[]): FolderRow {
  const today = Date.parse(new Date().toISOString().slice(0, 10))
  const start = today - 29 * DAY
  const daily = Array.from({ length: 30 }, (_, i) => ({ date: new Date(start + i * DAY).toISOString().slice(0, 10), count: 0 }))
  const status_counts = { draft: 0, published: 0, closed: 0, archived: 0 }
  let responses = 0
  let previous = 0
  let last = 0
  const owners = new Map<string, string>()
  for (const form of forms) {
    status_counts[form.status as keyof typeof status_counts]++
    owners.set(form.owner.id, form.owner.name)
    last = Math.max(last, Date.parse(form.updated_at))
    for (const entry of formResponses(tenant, form)) {
      responses++
      last = Math.max(last, entry.at)
      const day = Math.floor((entry.at - start) / DAY)
      if (day >= 0 && day < 30) daily[day]!.count++
      else if (day < 0 && day >= -30) previous++
    }
  }
  const published = forms.filter(form => form.status === 'published')
  return {
    id: folder.id,
    name: folder.name,
    color: folder.color ?? null,
    // Like the forms list: archived forms are not counted (the status card still shows them).
    forms_count: forms.filter(form => form.status !== 'archived').length,
    status_counts,
    responses_count: responses,
    responses_30d: daily.reduce((sum, day) => sum + day.count, 0),
    previous_30d: previous,
    daily,
    completion_rate: published.length ? Math.round(published.reduce((sum, form) => sum + form.completion_rate, 0) / published.length) : null,
    last_activity_at: last ? new Date(last).toISOString() : null,
    owners: [...owners].slice(0, 5).map(([id, name]) => ({ id, name })),
  }
}

const formsIn = (tenant: MockTenant, user: MockUser, folderId: string) => formsOf(tenant).forms.filter(form => !form.deleted_at && form.folder?.id === folderId && canSee(form, user))

/** GET /folders/overview, every folder with its numbers; q (name), sort, paged. */
export const folderOverview = defineMockRoute(({ event, query }) => {
  const { tenant, user } = requireAuth(event)
  const rows = formsOf(tenant).folders.map(folder => rowOf(tenant, folder, formsIn(tenant, user, folder.id)))
  const { data, meta } = paginate(rows, { sort: 'name', ...query }, (row, q) => row.name.toLowerCase().includes(q))
  return ok(data, meta)
})

/** GET /folders/:id, one folder with its numbers (the folder page). */
export const getFolder = defineMockRoute(({ event }) => {
  const { tenant, user } = requireAuth(event)
  const folder = formsOf(tenant).folders.find(item => item.id === getRouterParam(event, 'id'))
  if (!folder) throw new MockError('FRM-GEN-1004')
  return ok(rowOf(tenant, folder, formsIn(tenant, user, folder.id)))
})

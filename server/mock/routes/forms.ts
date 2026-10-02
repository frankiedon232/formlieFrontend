import type { FormSummary } from '#shared/types/forms'
import { defineMockRoute } from '../core/route'
import { ok, paginate } from '../core/respond'
import { MOCK_FOLDERS, MOCK_FORMS } from '../data/forms'

const filterValue = (query: Record<string, unknown>, key: string) => {
  const value = query[`filter[${key}]`]
  return typeof value === 'string' && value ? value.split(',') : null
}

/** GET /forms — filters: status, folder_id, owner_id, tag (comma = any of), from/to on updated_at. */
export const listForms = defineMockRoute(({ query }) => {
  const status = filterValue(query, 'status')
  const folder = filterValue(query, 'folder_id')
  const owner = filterValue(query, 'owner_id')
  const tag = filterValue(query, 'tag')
  const from = typeof query.from === 'string' && query.from ? Date.parse(`${query.from}T00:00:00Z`) : null
  const to = typeof query.to === 'string' && query.to ? Date.parse(`${query.to}T23:59:59Z`) : null

  const filtered = MOCK_FORMS.filter(form => {
    const updated = Date.parse(form.updated_at)
    return (
      // Archived forms only show when asked for explicitly.
      (status ? status.includes(form.status) : form.status !== 'archived') &&
      (!folder || (form.folder && folder.includes(form.folder.id))) &&
      (!owner || owner.includes(form.owner.id)) &&
      (!tag || form.tags.some(t => tag.includes(t))) &&
      (from === null || updated >= from) &&
      (to === null || updated <= to)
    )
  })

  const { data, meta } = paginate<FormSummary>(
    filtered,
    { sort: '-updated_at', ...query },
    (form, q) => form.name.toLowerCase().includes(q) || form.slug.includes(q),
  )
  return ok(data, meta)
})

/** GET /folders — the tenant's form folders. */
export const listFolders = defineMockRoute(() => ok(MOCK_FOLDERS))

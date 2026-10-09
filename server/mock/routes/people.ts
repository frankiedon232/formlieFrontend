/**
 * People (F16 Users & profiles, docs/API-CONTRACT.md → People). Admins and owners only until F22 adds
 * permissions.
 *
 *   GET /people              rows: ?q (name, email, departments, job titles), filter[status] · filter[role] ·
 *                            filter[department] · filter[job_title] (comma lists), sort, page, page_size
 *   GET /people/insights     the two cards on top
 *   GET /people/:id          one person's detail
 */
import type { PeopleInsights, PersonRow } from '#shared/types/people'
import { PERSON_STATUSES, WORKSPACE_ROLES } from '#shared/types/people'
import { auditLogOf } from '../core/audit'
import { requireAdmin } from '../core/auth'
import { MockError, ok, paginate } from '../core/respond'
import { defineMockRoute } from '../core/route'
import { peopleRows, personDetail } from '../data/peopleStore'

const DAY = 86_400_000
const listOf = (value: unknown) => (typeof value === 'string' && value ? value.split(',') : null)
const ORDER = { owner: 0, admin: 1, member: 2 } as const

export const listPeople = defineMockRoute(({ event, query }) => {
  const { tenant } = requireAdmin(event)
  const status = listOf(query['filter[status]'])
  const role = listOf(query['filter[role]'])
  const department = listOf(query['filter[department]'])
  const job = listOf(query['filter[job_title]'])
  let rows = peopleRows(tenant).filter(
    row =>
      (!status || status.includes(row.status)) &&
      (!role || role.includes(row.role)) &&
      (!department || row.departments.some(item => department.includes(item.id))) &&
      (!job || row.job_titles.some(item => job.includes(item.id))),
  )
  const sort = typeof query.sort === 'string' && query.sort ? query.sort : 'name'
  const key = sort.replace(/^-/, '')
  const sign = sort.startsWith('-') ? -1 : 1
  const value = (row: PersonRow): string | number => (key === 'role' ? ((ORDER as Record<string, number>)[row.role] ?? 3) : key === 'last_active_at' ? (row.last_active_at ? Date.parse(row.last_active_at) : 0) : key === 'joined_at' ? Date.parse(row.joined_at) : row.name.toLowerCase())
  rows = rows.sort((a, b) => {
    const x = value(a)
    const y = value(b)
    return (x < y ? -1 : x > y ? 1 : a.name.localeCompare(b.name)) * sign
  })
  const { data, meta } = paginate(rows, { ...query, sort: undefined }, (row, q) => `${row.name} ${row.email} ${row.departments.map(item => item.name).join(' ')} ${row.job_titles.map(item => item.name).join(' ')}`.toLowerCase().includes(q))
  return ok(data, meta)
})

export const peopleInsights = defineMockRoute(({ event }) => {
  const { tenant } = requireAdmin(event)
  const rows = peopleRows(tenant)
  const now = Date.now()
  const today = new Date(new Date().toISOString().slice(0, 10)).getTime()
  const daily = Array.from({ length: 30 }, (_, i) => ({ date: new Date(today - (29 - i) * DAY).toISOString().slice(0, 10), count: 0 }))
  const ids = new Set(rows.map(row => row.id))
  for (const item of auditLogOf(tenant)) {
    if (item.action !== 'auth.login.succeeded' || !item.actor.id || !ids.has(item.actor.id)) continue
    const index = 29 - Math.floor((today - new Date(item.occurred_at.slice(0, 10)).getTime()) / DAY)
    if (index >= 0 && index < 30) daily[index]!.count++
  }
  const by_status = Object.fromEntries(PERSON_STATUSES.map(status => [status, rows.filter(row => row.status === status).length])) as PeopleInsights['by_status']
  const by_role = Object.fromEntries(WORKSPACE_ROLES.map(role => [role, rows.filter(row => row.role === role).length])) as PeopleInsights['by_role']
  return ok<PeopleInsights>({
    total: rows.length,
    joined: rows.filter(row => now - Date.parse(row.joined_at) < 30 * DAY).length,
    joined_previous: rows.filter(row => now - Date.parse(row.joined_at) >= 30 * DAY && now - Date.parse(row.joined_at) < 60 * DAY).length,
    two_step: rows.filter(row => row.two_step).length,
    by_status,
    by_role,
    daily,
  })
})

export const getPerson = defineMockRoute(({ event }) => {
  const { tenant } = requireAdmin(event)
  const detail = personDetail(tenant, getRouterParam(event, 'id') ?? '')
  if (!detail) throw new MockError('FRM-GEN-1004')
  return ok(detail)
})

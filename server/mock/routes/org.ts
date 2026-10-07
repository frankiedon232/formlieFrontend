/**
 * Organisation data (F14 M2, docs/API-CONTRACT.md → Organisation data). Admins only; the builder reads the
 * same lists through /directory. `:kind` = departments · job_titles · teams · locations · cost_centres.
 *
 *   GET    /org/:kind                 list (q, sort, filter[status]) · /insights · /:id · /:id/usage
 *   POST   /org/:kind                 { name, code, description, member_ids } → the entry (names unique per kind)
 *   PATCH  /org/:kind/:id             the same
 *   POST   /org/:kind/:id/archive     archived entries stay on forms that use them, flagged · /restore
 *   POST   /org/:kind/merge           { from: [ids], into: id } people and forms move to `into`, the rest go
 *   POST   /org/:kind/import          { names: [] } → { created, skipped }
 *   DELETE /org/:kind/:id             only when no form uses it (else FRM-ORG-1002)
 */
import { z } from 'zod'
import type { OrgImportResult, OrgInsights, OrgKind } from '#shared/types/org'
import { ORG_KINDS } from '#shared/types/org'
import { actorOf, recordAudit } from '../core/audit'
import { requireAdmin } from '../core/auth'
import { filtersOf, MockError, ok, paginate } from '../core/respond'
import { defineMockRoute } from '../core/route'
import { parseBody } from '../core/validate'
import { saveForms } from '../data/formStore'
import { moveAudience, orgOf, peopleOf, saveOrg, toOrgItem, usageOf, type StoredOrgItem } from '../data/orgStore'
import type { MockTenant } from '../data/tenants'

const LABEL: Record<OrgKind, string> = { departments: 'Department', job_titles: 'Job title', teams: 'Team', locations: 'Location', cost_centres: 'Cost centre' }
const optional = (max: number) => z.string().trim().max(max).nullable().transform(value => value || null)
const input = z.object({ name: z.string().trim().min(1).max(80), code: optional(20), description: optional(200), member_ids: z.array(z.string().max(100)).max(1000) })

function kindOf(value: string | undefined): OrgKind {
  if (!value || !(ORG_KINDS as readonly string[]).includes(value)) throw new MockError('FRM-GEN-1004')
  return value as OrgKind
}
function find(tenant: MockTenant, kind: OrgKind, id: string | undefined) {
  const item = orgOf(tenant)[kind].find(entry => entry.id === id)
  if (!item) throw new MockError('FRM-GEN-1004')
  return item
}
function checked(tenant: MockTenant, kind: OrgKind, values: z.infer<typeof input>, exceptId?: string) {
  if (orgOf(tenant)[kind].some(item => item.id !== exceptId && item.name.toLowerCase() === values.name.toLowerCase())) throw new MockError('FRM-ORG-1001', [{ field: 'name', message: 'taken' }])
  const people = new Set(peopleOf(tenant).map(person => person.id))
  return { ...values, member_ids: [...new Set(values.member_ids.filter(id => people.has(id)))] }
}
const resource = (kind: OrgKind, item: StoredOrgItem) => ({ type: kind.replace(/s$/, ''), id: item.id, name: item.name })

export const listOrg = defineMockRoute(({ event, query }) => {
  const { tenant } = requireAdmin(event)
  const kind = kindOf(getRouterParam(event, 'kind'))
  const filter = filtersOf(query)
  const people = peopleOf(tenant)
  let rows = orgOf(tenant)[kind].map(item => toOrgItem(tenant, kind, item, people))
  // in_use: active with people · empty: active, nobody in it · archived
  const state = (row: (typeof rows)[number]) => (row.status === 'archived' ? 'archived' : row.members.length ? 'in_use' : 'empty')
  if (filter.status) rows = rows.filter(row => filter.status!.split(',').includes(state(row)))
  const sort = typeof query.sort === 'string' && query.sort ? query.sort : 'name'
  const desc = sort.startsWith('-')
  const key = desc ? sort.slice(1) : sort
  const value = (row: (typeof rows)[number]) => (key === 'members' ? row.members.length : key === 'forms' ? row.forms_count : key === 'updated_at' ? row.updated_at : key === 'created_at' ? row.created_at : row.name.toLowerCase())
  rows.sort((a, b) => {
    const x = value(a)
    const y = value(b)
    const order = typeof x === 'number' && typeof y === 'number' ? x - y : String(x).localeCompare(String(y))
    return desc ? -order : order
  })
  const { data, meta } = paginate(rows, { ...query, sort: undefined }, (row, q) => `${row.name} ${row.code ?? ''} ${row.description ?? ''}`.toLowerCase().includes(q))
  return ok(data, meta)
})

export const orgInsights = defineMockRoute(({ event }) => {
  const { tenant } = requireAdmin(event)
  const kind = kindOf(getRouterParam(event, 'kind'))
  const items = orgOf(tenant)[kind]
  const active = items.filter(item => !item.archived_at)
  const people = peopleOf(tenant)
  const assigned = new Set(active.flatMap(item => item.member_ids))
  const insights: OrgInsights = {
    total: items.length,
    by_status: { active: active.length, archived: items.length - active.length },
    people: people.length,
    people_assigned: people.filter(person => assigned.has(person.id)).length,
    empty: active.filter(item => !item.member_ids.length).length,
    largest: [...active].sort((a, b) => b.member_ids.length - a.member_ids.length).slice(0, 12).map(item => ({ id: item.id, name: item.name, count: item.member_ids.length })),
  }
  return ok(insights)
})

export const getOrgItem = defineMockRoute(({ event }) => {
  const { tenant } = requireAdmin(event)
  const kind = kindOf(getRouterParam(event, 'kind'))
  return ok(toOrgItem(tenant, kind, find(tenant, kind, getRouterParam(event, 'id'))))
})

export const orgUsage = defineMockRoute(({ event }) => {
  const { tenant } = requireAdmin(event)
  const kind = kindOf(getRouterParam(event, 'kind'))
  const item = find(tenant, kind, getRouterParam(event, 'id'))
  return ok(usageOf(tenant, kind, item.id))
})

export const createOrgItem = defineMockRoute(({ event, body }) => {
  const { tenant, user } = requireAdmin(event)
  const kind = kindOf(getRouterParam(event, 'kind'))
  const values = checked(tenant, kind, parseBody(input, body))
  const now = new Date().toISOString()
  const item: StoredOrgItem = { id: crypto.randomUUID(), ...values, archived_at: null, created_at: now, updated_at: now }
  orgOf(tenant)[kind].push(item)
  saveOrg()
  recordAudit(event, tenant, { action: 'settings.org_created', actor: actorOf(user), resource: resource(kind, item), metadata: { kind: LABEL[kind], people: String(item.member_ids.length) } })
  return ok(toOrgItem(tenant, kind, item), {}, 201)
})

export const updateOrgItem = defineMockRoute(({ event, body }) => {
  const { tenant, user } = requireAdmin(event)
  const kind = kindOf(getRouterParam(event, 'kind'))
  const item = find(tenant, kind, getRouterParam(event, 'id'))
  const values = checked(tenant, kind, parseBody(input, body), item.id)
  const before = { name: item.name, code: item.code, description: item.description, people: String(item.member_ids.length) }
  Object.assign(item, values, { updated_at: new Date().toISOString() })
  saveOrg()
  const after = { name: item.name, code: item.code, description: item.description, people: String(item.member_ids.length) }
  const changes = (Object.keys(after) as (keyof typeof after)[]).filter(key => before[key] !== after[key]).map(field => ({ field, before: before[field], after: after[field] }))
  if (changes.length) recordAudit(event, tenant, { action: 'settings.org_updated', actor: actorOf(user), resource: resource(kind, item), changes, metadata: { kind: LABEL[kind] } })
  return ok(toOrgItem(tenant, kind, item))
})

function setArchived(archive: boolean) {
  return defineMockRoute(({ event }) => {
    const { tenant, user } = requireAdmin(event)
    const kind = kindOf(getRouterParam(event, 'kind'))
    const item = find(tenant, kind, getRouterParam(event, 'id'))
    if (!!item.archived_at !== archive) {
      item.archived_at = archive ? new Date().toISOString() : null
      item.updated_at = new Date().toISOString()
      saveOrg()
      recordAudit(event, tenant, { action: archive ? 'settings.org_archived' : 'settings.org_restored', actor: actorOf(user), resource: resource(kind, item), metadata: { kind: LABEL[kind] } })
    }
    return ok(toOrgItem(tenant, kind, item))
  })
}
export const archiveOrgItem = setArchived(true)
export const restoreOrgItem = setArchived(false)

export const mergeOrgItems = defineMockRoute(({ event, body }) => {
  const { tenant, user } = requireAdmin(event)
  const kind = kindOf(getRouterParam(event, 'kind'))
  const { from, into } = parseBody(z.object({ from: z.array(z.string()).min(1).max(100), into: z.string() }), body)
  const target = find(tenant, kind, into)
  const sources = [...new Set(from)].filter(id => id !== into).map(id => find(tenant, kind, id))
  if (!sources.length) throw new MockError('FRM-GEN-1002', [{ field: 'from', message: 'required' }])
  target.member_ids = [...new Set([...target.member_ids, ...sources.flatMap(item => item.member_ids)])]
  target.updated_at = new Date().toISOString()
  const fields = moveAudience(tenant, kind, sources.map(item => item.id), target.id)
  const store = orgOf(tenant)
  store[kind] = store[kind].filter(item => !sources.includes(item))
  saveOrg()
  if (fields) saveForms()
  recordAudit(event, tenant, { action: 'settings.org_merged', actor: actorOf(user), resource: resource(kind, target), metadata: { kind: LABEL[kind], merged: sources.map(item => item.name).join(', '), fields: String(fields) } })
  return ok(toOrgItem(tenant, kind, target))
})

export const importOrgItems = defineMockRoute(({ event, body }) => {
  const { tenant, user } = requireAdmin(event)
  const kind = kindOf(getRouterParam(event, 'kind'))
  const { names } = parseBody(z.object({ names: z.array(z.string()).min(1).max(1000) }), body)
  const store = orgOf(tenant)[kind]
  const taken = new Set(store.map(item => item.name.toLowerCase()))
  const result: OrgImportResult = { created: 0, skipped: [] }
  const now = new Date().toISOString()
  for (const raw of names) {
    const name = raw.trim()
    if (!name) continue
    if (name.length > 80) result.skipped.push({ name: name.slice(0, 80), reason: 'too_long' })
    else if (taken.has(name.toLowerCase())) result.skipped.push({ name, reason: 'duplicate' })
    else {
      taken.add(name.toLowerCase())
      store.push({ id: crypto.randomUUID(), name, code: null, description: null, member_ids: [], archived_at: null, created_at: now, updated_at: now })
      result.created++
    }
  }
  saveOrg()
  if (result.created) recordAudit(event, tenant, { action: 'settings.org_imported', actor: actorOf(user), resource: { type: kind, id: null, name: LABEL[kind] }, metadata: { created: String(result.created), skipped: String(result.skipped.length) } })
  return ok(result)
})

export const deleteOrgItem = defineMockRoute(({ event }) => {
  const { tenant, user } = requireAdmin(event)
  const kind = kindOf(getRouterParam(event, 'kind'))
  const item = find(tenant, kind, getRouterParam(event, 'id'))
  const usage = usageOf(tenant, kind, item.id)
  if (usage.length) throw new MockError('FRM-ORG-1002', usage.slice(0, 5).map(entry => ({ field: 'form', message: entry.form.name })))
  const store = orgOf(tenant)
  store[kind] = store[kind].filter(entry => entry !== item)
  saveOrg()
  recordAudit(event, tenant, { action: 'settings.org_deleted', actor: actorOf(user), resource: resource(kind, item), metadata: { kind: LABEL[kind] } })
  return ok({ deleted: true })
})

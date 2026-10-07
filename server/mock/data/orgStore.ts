/**
 * Organisation data in the mock (F14 M2), kept in `.data/mock/org.json`: each workspace's departments,
 * job titles, teams, locations and cost centres, with the people in them. New workspaces start empty
 * (owner, 2026-10-03: no built-in samples once Settings exist); the demo workspaces keep the sample
 * departments their forms already use (same ids) and a few job titles.
 */
import type { OrgItem, OrgKind, OrgPerson, OrgUsage } from '#shared/types/org'
import { ORG_KINDS } from '#shared/types/org'
import { allFields } from '#shared/utils/forms/build'
import { loadPersisted, savePersisted } from '../core/persist'
import { MOCK_OWNERS } from './forms'
import { formsOf } from './formStore'
import { MOCK_USERS, SEEDED_TENANT_IDS, type MockTenant } from './tenants'

export interface StoredOrgItem {
  id: string
  name: string
  code: string | null
  description: string | null
  member_ids: string[]
  archived_at: string | null
  created_at: string
  updated_at: string
}
type TenantOrg = Record<OrgKind, StoredOrgItem[]>

const stores = new Map<string, TenantOrg>(Object.entries(loadPersisted<Record<string, TenantOrg>>('org', {})))
export const saveOrg = () => savePersisted('org', () => Object.fromEntries(stores))

/** Field access mode for each kind that fields can be restricted to. */
export const AUDIENCE_MODE: Partial<Record<OrgKind, string>> = { departments: 'department', job_titles: 'job_title' }

/** The people of a workspace (members and the sample form owners), as the directory lists them. */
export function peopleOf(tenant: MockTenant): OrgPerson[] {
  const domain = `${tenant.subdomain}.test`
  return [
    ...MOCK_USERS.filter(user => user.tenant_id === tenant.id && !user.disabled).map(user => ({ id: user.id, name: `${user.first_name} ${user.last_name}`.trim(), email: user.email })),
    ...MOCK_OWNERS.map(owner => ({ id: owner.id, name: owner.name, email: `${owner.name.toLowerCase().replace(/\s+/g, '.')}@${domain}` })),
  ]
}

const DEPARTMENTS = ['Finance', 'Operations', 'People', 'Sales', 'Support', 'Technology', 'Legal', 'Compliance']
const JOB_TITLES = ['Manager', 'Team lead', 'Specialist', 'Coordinator', 'Analyst', 'Assistant']

function seed(tenant: MockTenant): TenantOrg {
  const empty = Object.fromEntries(ORG_KINDS.map(kind => [kind, [] as StoredOrgItem[]])) as TenantOrg
  if (!SEEDED_TENANT_IDS.has(tenant.id)) return empty
  const people = peopleOf(tenant)
  const at = new Date(Date.now() - 60 * 86_400_000).toISOString()
  const item = (id: string, name: string, members: string[]): StoredOrgItem => ({ id, name, code: null, description: null, member_ids: members, archived_at: null, created_at: at, updated_at: at })
  // Everyone in one department, the last two departments left empty so the page shows both cases
  empty.departments = DEPARTMENTS.map((name, i) => item(`dep_${name.toLowerCase()}`, name, i < 6 ? people.filter((_, p) => p % 6 === i).map(person => person.id) : []))
  empty.job_titles = JOB_TITLES.map((name, i) => item(`job_${name.toLowerCase().replace(/\s+/g, '_')}`, name, people.filter((_, p) => p % JOB_TITLES.length === i).map(person => person.id)))
  return empty
}

export function orgOf(tenant: MockTenant): TenantOrg {
  let store = stores.get(tenant.id)
  if (!store) {
    store = seed(tenant)
    stores.set(tenant.id, store)
    saveOrg()
  }
  for (const kind of ORG_KINDS) store[kind] ??= []
  return store
}

/** Forms with a field restricted to this entry, and those fields' labels. */
export function usageOf(tenant: MockTenant, kind: OrgKind, id: string): OrgUsage[] {
  const mode = AUDIENCE_MODE[kind]
  if (!mode) return []
  return formsOf(tenant)
    .forms.filter(form => !form.deleted_at)
    .flatMap(form => {
      const fields = [form.schema, form.published_schema].flatMap(schema => (schema ? allFields(schema) : [])).filter(field => field.audience?.mode === mode && field.audience.ids?.includes(id))
      const labels = [...new Set(fields.map(field => field.label || field.key))]
      return labels.length ? [{ form: { id: form.id, name: form.name, status: form.status }, fields: labels }] : []
    })
}

export function toOrgItem(tenant: MockTenant, kind: OrgKind, item: StoredOrgItem, people = peopleOf(tenant)): OrgItem {
  return {
    id: item.id,
    kind,
    name: item.name,
    code: item.code,
    description: item.description,
    status: item.archived_at ? 'archived' : 'active',
    members: item.member_ids.map(id => people.find(person => person.id === id)).filter((person): person is OrgPerson => !!person),
    forms_count: usageOf(tenant, kind, item.id).length,
    created_at: item.created_at,
    updated_at: item.updated_at,
    archived_at: item.archived_at,
  }
}

/** Fields restricted to `from` are restricted to `into` instead (merging entries). */
export function moveAudience(tenant: MockTenant, kind: OrgKind, from: string[], into: string) {
  const mode = AUDIENCE_MODE[kind]
  if (!mode) return 0
  let moved = 0
  for (const form of formsOf(tenant).forms)
    for (const schema of [form.schema, form.published_schema])
      for (const field of schema ? allFields(schema) : []) {
        const ids = field.audience?.mode === mode ? field.audience.ids : undefined
        if (!ids?.some(id => from.includes(id))) continue
        field.audience!.ids = [...new Set(ids.map(id => (from.includes(id) ? into : id)))]
        moved++
      }
  return moved
}

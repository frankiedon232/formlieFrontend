/**
 * Saved queries in the mock (F12 M4 part 2): per workspace, personal or shared, kept in
 * `.data/mock/saved-queries.json`. A few believable ones are seeded on the workspace's first
 * connection the first time it is read; runs from the editor are counted day by day.
 */
import type { SavedQuery } from '#shared/types/query'
import { scriptKind } from '#shared/utils/datasources/sql'
import { loadPersisted, savePersisted } from '../core/persist'
import { seedOf } from './dataSourceSim'
import { dataSourcesOf, type StoredDataSource } from './dataSourceStore'
import { MOCK_USERS, type MockTenant, type MockUser } from './tenants'

export interface StoredSavedQuery {
  id: string
  name: string
  description: string | null
  sql: string
  datasource_id: string
  shared: boolean
  owner_id: string
  /** ISO day → runs that day. */
  runs: Record<string, number>
  last_run_at: string | null
  created_at: string
  updated_at: string
}

const DAY = 86_400_000
const stores = new Map<string, StoredSavedQuery[]>(Object.entries(loadPersisted<Record<string, StoredSavedQuery[]>>('saved-queries', {})))
export const saveSavedQueries = () => savePersisted('saved-queries', () => Object.fromEntries(stores))
const day = (time: number) => new Date(time).toISOString().slice(0, 10)

const SEEDS: { name: string; description: string | null; sql: (source: StoredDataSource) => string; shared: boolean }[] = [
  { name: 'Newest clients', description: 'The 50 clients added last.', sql: () => 'SELECT id, full_name, email, created_at\nFROM public.clients\nORDER BY created_at DESC\nLIMIT 50;', shared: true },
  { name: 'Clients without a phone number', description: 'Who to ask for a phone number.', sql: () => 'SELECT id, full_name, email\nFROM public.clients\nWHERE phone IS NULL\nORDER BY full_name;', shared: true },
  { name: 'Open cases', description: null, sql: () => "SELECT id, client_id, title, opened_on\nFROM intake.cases\nWHERE status = 'open'\nORDER BY opened_on;", shared: false },
  { name: 'Referrals by email', description: 'Look up a person: fill in :email.', sql: () => 'SELECT *\nFROM public.referrals\nWHERE email = :email;', shared: false },
]

/** The workspace's saved queries (seeded once on its first connection). */
export function savedQueriesOf(tenant: MockTenant): StoredSavedQuery[] {
  let list = stores.get(tenant.id)
  if (!list) {
    const source = dataSourcesOf(tenant)[0]
    const owner = MOCK_USERS.find(user => user.tenant_id === tenant.id && user.role === 'owner') ?? MOCK_USERS.find(user => user.tenant_id === tenant.id)
    list = source && owner
      ? SEEDS.map((seed, index) => {
          const created = Date.now() - (40 - index * 7) * DAY
          const runs: Record<string, number> = {}
          for (let n = 0; n < 30; n++) {
            const count = seedOf(`${tenant.id}${index}${n}`) % (index === 0 ? 7 : 4)
            if (count) runs[day(Date.now() - n * DAY)] = count
          }
          return { id: crypto.randomUUID(), name: seed.name, description: seed.description, sql: seed.sql(source), datasource_id: source.id, shared: seed.shared, owner_id: owner.id, runs, last_run_at: new Date(Date.now() - (index + 1) * 3_600_000).toISOString(), created_at: new Date(created).toISOString(), updated_at: new Date(created + DAY).toISOString() }
        })
      : []
    stores.set(tenant.id, list)
    saveSavedQueries()
  }
  return list
}

/** Saved queries this person may see: theirs and the shared ones. */
export const visibleTo = (tenant: MockTenant, user: MockUser) => savedQueriesOf(tenant).filter(item => item.shared || item.owner_id === user.id)

export function countRun(tenant: MockTenant, id: string) {
  const item = savedQueriesOf(tenant).find(entry => entry.id === id)
  if (!item) return
  const today = day(Date.now())
  item.runs[today] = (item.runs[today] ?? 0) + 1
  item.last_run_at = new Date().toISOString()
  saveSavedQueries()
}

export function toSavedQuery(tenant: MockTenant, user: MockUser, item: StoredSavedQuery): SavedQuery {
  const source = dataSourcesOf(tenant).find(entry => entry.id === item.datasource_id)
  const owner = MOCK_USERS.find(entry => entry.id === item.owner_id)
  const daily = Array.from({ length: 30 }, (_, index) => {
    const date = day(Date.now() - (29 - index) * DAY)
    return { date, count: item.runs[date] ?? 0 }
  })
  return {
    id: item.id,
    name: item.name,
    description: item.description,
    sql: item.sql,
    kind: scriptKind(item.sql),
    datasource: { id: item.datasource_id, name: source?.name ?? '', engine: source?.engine ?? 'postgresql' },
    shared: item.shared,
    mine: item.owner_id === user.id,
    owner: { id: item.owner_id, name: owner ? `${owner.first_name} ${owner.last_name}` : '' },
    run_count: Object.values(item.runs).reduce((sum, count) => sum + count, 0),
    last_run_at: item.last_run_at,
    daily,
    created_at: item.created_at,
    updated_at: item.updated_at,
  }
}

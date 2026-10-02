/**
 * Per-workspace reusable building blocks for the mock: saved fields and option lists.
 * Seeded workspaces start with a few neutral sample lists. Persisted across dev reloads.
 */
import type { OptionList, SavedField } from '#shared/types/forms'
import { loadPersisted, savePersisted } from '../core/persist'
import { SEEDED_TENANT_IDS, type MockTenant } from './tenants'

interface TenantLibrary {
  fields: SavedField[]
  lists: OptionList[]
}

const stores = new Map<string, TenantLibrary>(
  Object.entries(loadPersisted<Record<string, TenantLibrary>>('library', {})),
)

const SYSTEM = { id: 'system', name: 'Formalie' }
const at = '2026-09-01T09:00:00.000Z'
const list = (id: string, name: string, labels: string[]): OptionList => ({
  id,
  name,
  options: labels.map(label => ({ value: label.toLowerCase().replace(/[^a-z0-9]+/g, '_'), label })),
  created_by: SYSTEM,
  created_at: at,
  updated_at: at,
})
const SAMPLE_LISTS = () => [
  list('lst_priority', 'Priority', ['Low', 'Medium', 'High', 'Critical']),
  list('lst_departments', 'Departments', ['Finance', 'Operations', 'People', 'Sales', 'Support', 'Technology']),
  list('lst_weekdays', 'Days of the week', ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']),
  list('lst_satisfaction', 'Satisfaction', ['Very unhappy', 'Unhappy', 'Neutral', 'Happy', 'Very happy']),
]

export function libraryOf(tenant: MockTenant): TenantLibrary {
  let store = stores.get(tenant.id)
  if (!store) {
    store = { fields: [], lists: SEEDED_TENANT_IDS.has(tenant.id) ? SAMPLE_LISTS() : [] }
    stores.set(tenant.id, store)
  }
  return store
}

export const saveLibrary = () => savePersisted('library', () => Object.fromEntries(stores))

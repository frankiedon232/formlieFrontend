/**
 * Per-workspace reusable building blocks for the mock: saved fields and option lists.
 * Seeded workspaces start with a few neutral sample lists. Persisted across dev reloads.
 */
import type { OptionList, SavedField, SavedTheme } from '#shared/types/forms'
import type { FormSchemaV1 } from '#shared/utils/forms/schema'
import { loadPersisted, savePersisted } from '../core/persist'
import { SEEDED_TENANT_IDS, type MockTenant } from './tenants'

interface TenantLibrary {
  fields: SavedField[]
  lists: OptionList[]
  /** Saved designs; `forms_count` is computed when listing. */
  themes?: Omit<SavedTheme, 'forms_count'>[]
  /** Workspace templates (F9): a snapshot of a form, its design included. */
  templates?: WorkspaceTemplate[]
}

export interface WorkspaceTemplate {
  id: string
  name: string
  description: string
  category: string
  icon: string
  schema: FormSchemaV1
  created_by: { id: string; name: string }
  created_at: string
  updated_at: string
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

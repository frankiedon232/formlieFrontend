/**
 * Per-workspace forms and folders for the mock. Seeded workspaces start with the sample forms
 * (a copy each); a new workspace starts empty. Persisted across dev reloads (../core/persist.ts).
 * Trash is emptied automatically after TRASH_RETENTION_DAYS.
 */
import { TRASH_RETENTION_DAYS, type FormFolder, type FormStatus, type FormSummary, type FormVersion } from '#shared/types/forms'
import type { FormSchemaV1 } from '#shared/utils/forms/schema'
import { loadPersisted, savePersisted } from '../core/persist'
import { MOCK_FOLDERS, MOCK_FORMS, SEED_TEMPLATES, seedBaseName } from './forms'
import { SEEDED_TENANT_IDS, type MockTenant } from './tenants'

export interface StoredForm extends FormSummary {
  /** Status before archiving, so unarchive puts it back. */
  previous_status: FormStatus | null
  schema: FormSchemaV1 | null
  template_key: string | null
  /** What respondents see (null until first publish). */
  published_schema?: FormSchemaV1 | null
  versions?: StoredVersion[]
}

export interface StoredVersion extends FormVersion {
  schema: FormSchemaV1
}

interface TenantForms {
  forms: StoredForm[]
  folders: FormFolder[]
  /** Sample forms linked to their templates (F9 migration done). */
  templatesSeeded?: boolean
}

const DAY = 86_400_000
const stores = new Map<string, TenantForms>(
  Object.entries(loadPersisted<Record<string, TenantForms>>('forms', {})),
)

export function formsOf(tenant: MockTenant): TenantForms {
  let store = stores.get(tenant.id)
  if (!store) {
    store = SEEDED_TENANT_IDS.has(tenant.id)
      ? {
          forms: MOCK_FORMS.map(form => ({
            ...structuredClone(form),
            previous_status: form.status === 'archived' ? 'closed' : null,
            schema: null,
            template_key: SEED_TEMPLATES[seedBaseName(form.name)] ?? null,
          })),
          folders: MOCK_FOLDERS.map(folder => ({ ...folder })),
        }
      : { forms: [], folders: [] }
    stores.set(tenant.id, store)
  } else if (SEEDED_TENANT_IDS.has(tenant.id) && !store.templatesSeeded) {
    // Stores saved before F9: link untouched sample forms to their template once.
    for (const form of store.forms)
      if (!form.template_key && !form.schema) form.template_key = SEED_TEMPLATES[seedBaseName(form.name)] ?? null
    store.templatesSeeded = true
    saveForms()
  }
  const cutoff = Date.now() - TRASH_RETENTION_DAYS * DAY
  const before = store.forms.length
  store.forms = store.forms.filter(form => !form.deleted_at || Date.parse(form.deleted_at) > cutoff)
  if (store.forms.length !== before) saveForms()
  return store
}

export function saveForms() {
  savePersisted('forms', () => Object.fromEntries(stores))
}

/** The public view of a stored form (internal fields removed). */
export function summaryOf(form: StoredForm): FormSummary {
  const {
    previous_status: _p,
    schema: _s,
    template_key: _t,
    published_schema: _ps,
    versions: _v,
    ...summary
  } = form
  return summary
}

export const slugify = (value: string) =>
  value
    .toLowerCase()
    .normalize('NFKD')
    .replace(/[̀-ͯ]/g, '')
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/(^-|-$)/g, '')
    .slice(0, 60) || 'form'

/** A slug not used by another form of this workspace (`name`, `name-2`, …). */
export function uniqueSlug(store: TenantForms, name: string, exceptId?: string): string {
  const base = slugify(name)
  const taken = new Set(store.forms.filter(form => form.id !== exceptId).map(form => form.slug))
  if (!taken.has(base)) return base
  let n = 2
  while (taken.has(`${base}-${n}`)) n++
  return `${base}-${n}`
}

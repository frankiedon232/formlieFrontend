/**
 * Per-workspace forms and folders for the mock. Seeded workspaces start with the sample forms
 * (a copy each); a new workspace starts empty. Persisted across dev reloads (../core/persist.ts).
 * Trash is emptied automatically after TRASH_RETENTION_DAYS.
 */
import { TRASH_RETENTION_DAYS, type FormFolder, type FormStatus, type FormSummary, type FormVersion } from '#shared/types/forms'
import type { FormSchemaV1 } from '#shared/utils/forms/schema'
import { newPublicKey } from '#shared/utils/urls/public'
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
  /** Password for access "password" (F10 M3): scrypt hash + salt; the version invalidates unlocks when it changes. */
  password?: { hash: string; salt: string; version: number; changed_at: string } | null
  /** Short link (F10 M3): visits counted when it is opened. */
  short_clicks?: number
  short_created_at?: string | null
  /** Websites allowed to show the embed (F10 M3; empty / missing = any). */
  embed_domains?: string[]
}

export interface StoredVersion extends FormVersion {
  schema: FormSchemaV1
}

interface TenantForms {
  forms: StoredForm[]
  folders: FormFolder[]
  /** Sample forms linked to their templates (F9 migration done). */
  templatesSeeded?: boolean
  /** Sample forms given their availability dates (F10 migration done). */
  availabilitySeeded?: boolean
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
            public_key: newPublicKey(),
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
  // Stores saved before F10: give every form its public key once.
  if (store.forms.some(form => !form.public_key || form.closes_at === undefined)) {
    // Sample forms take their seeded availability dates once (so every state shows up).
    const seeds = new Map(MOCK_FORMS.map(seed => [seed.id, seed]))
    for (const form of store.forms) {
      form.public_key ||= newPublicKey()
      form.opens_at ??= seeds.get(form.id)?.opens_at ?? null
      form.closes_at ??= seeds.get(form.id)?.closes_at ?? null
    }
    saveForms()
  }
  if (SEEDED_TENANT_IDS.has(tenant.id) && !store.availabilitySeeded) {
    const seeds = new Map(MOCK_FORMS.map(seed => [seed.id, seed]))
    for (const form of store.forms) {
      const seed = seeds.get(form.id)
      if (!seed || form.opens_at || form.closes_at) continue
      form.opens_at = seed.opens_at
      form.closes_at = seed.closes_at
    }
    store.availabilitySeeded = true
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
    password: _pw,
    short_clicks: _sc,
    short_created_at: _sca,
    embed_domains: _ed,
    ...summary
  } = form
  // Share settings added in F10 M3: older forms have none yet.
  return { ...summary, custom_link: summary.custom_link ?? null, access: summary.access ?? 'public', response_limit: summary.response_limit ?? null, short_code: summary.short_code ?? null }
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

/** A form by its public key (unique everywhere) or custom link (unique per host: a workspace subdomain, or forms.* for workspaces without one). */
export function findByPublicKey(tenants: MockTenant[], key: string, { sharedHost = false } = {}): { tenant: MockTenant; form: StoredForm } | null {
  for (const tenant of tenants) {
    // The key, or the form's custom link (F10 M3).
    // On the shared forms host a custom link belongs to a workspace without its own subdomain.
    const linkHere = (item: StoredForm) => item.custom_link === key && !(sharedHost && tenant.subdomain)
    const form = formsOf(tenant).forms.find(item => (item.public_key === key || linkHere(item)) && !item.deleted_at)
    if (form) return { tenant, form }
  }
  return null
}

/** A form by its short link code, across workspaces (F10 M3). */
export function findByShortCode(tenants: MockTenant[], code: string): { tenant: MockTenant; form: StoredForm } | null {
  for (const tenant of tenants) {
    const form = formsOf(tenant).forms.find(item => item.short_code === code && !item.deleted_at)
    if (form) return { tenant, form }
  }
  return null
}

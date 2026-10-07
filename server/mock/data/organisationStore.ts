/**
 * Organisations in the mock (F14 M7), kept in `.data/mock/organisations.json`: the workspace's main
 * organisation (its existing one) plus any subsidiaries or branches. Forms point at one with
 * `organisation_id` (missing = the main one). `inScope()` narrows lists to the organisation the
 * person chose in the rail (header, see core/scope.ts).
 */
import type { Organisation } from '#shared/types/organisations'
import { loadPersisted, savePersisted } from '../core/persist'
import { scopedOrganisation } from '../core/scope'
import type { StoredForm } from './formStore'
import type { MockTenant } from './tenants'

export type StoredOrganisation = Omit<Organisation, 'forms_count' | 'responses_count'>

const stores = new Map<string, StoredOrganisation[]>(Object.entries(loadPersisted<Record<string, StoredOrganisation[]>>('organisations', {})))
export const saveOrganisations = () => savePersisted('organisations', () => Object.fromEntries(stores))

export function organisationsOf(tenant: MockTenant): StoredOrganisation[] {
  let list = stores.get(tenant.id)
  if (!list) {
    const at = new Date().toISOString()
    list = [{ id: tenant.organisation.id, name: tenant.organisation.name, short_name: null, logo_url: null, website: tenant.website ?? null, main: true, status: 'active', created_at: at, updated_at: at }]
    stores.set(tenant.id, list)
    saveOrganisations()
  }
  // The main one follows the workspace's company name (Settings → Company)
  const main = list.find(item => item.main)
  if (main && main.name !== tenant.organisation.name) main.name = tenant.organisation.name
  return list
}

/** The organisation a form belongs to. */
export const organisationOfForm = (tenant: MockTenant, form: Pick<StoredForm, 'organisation_id'>) => {
  const list = organisationsOf(tenant)
  return list.find(item => item.id === form.organisation_id) ?? list.find(item => item.main)!
}

/** In the organisation the person narrowed the portal to (always true when they see all). */
export function inScope(tenant: MockTenant, form: Pick<StoredForm, 'organisation_id'>): boolean {
  const scoped = scopedOrganisation()
  return !scoped || organisationOfForm(tenant, form).id === scoped
}

/** The organisation a new form goes to: the one chosen in the rail when it is active, else the main one. */
export function organisationForNewForm(tenant: MockTenant): string | null {
  const scoped = scopedOrganisation()
  const found = scoped ? organisationsOf(tenant).find(item => item.id === scoped && item.status === 'active' && !item.main) : null
  return found?.id ?? null
}

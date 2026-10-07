/**
 * Organisations (F14 M7, docs/API-CONTRACT.md → Organisations). Everyone can list them (the rail's
 * switcher); admins add, change, archive and restore them. The main one can't be archived.
 *
 *   GET   /organisations                         all, with forms and responses counts
 *   POST  /organisations                         OrganisationSaveRequest
 *   PATCH /organisations/:id                     OrganisationSaveRequest
 *   POST  /organisations/:id/archive · /restore  archived ones leave the switcher; their forms keep them
 *   PATCH /forms/:id/organisation                { organisation_id } (editors of the form)
 */
import { z } from 'zod'
import type { Organisation } from '#shared/types/organisations'
import { actorOf, recordAudit } from '../core/audit'
import { requireAdmin, requireAuth } from '../core/auth'
import { MockError, ok } from '../core/respond'
import { defineMockRoute } from '../core/route'
import { parseBody } from '../core/validate'
import { formsOf, saveForms, summaryOf } from '../data/formStore'
import { requireLevel } from '../data/formPermissions'
import { organisationOfForm, organisationsOf, saveOrganisations, type StoredOrganisation } from '../data/organisationStore'
import type { MockTenant, MockUser } from '../data/tenants'
import { completedUploadUrl } from './uploads'
import type { H3Event } from 'h3'

function counts(tenant: MockTenant) {
  const forms = new Map<string, number>()
  const responses = new Map<string, number>()
  for (const form of formsOf(tenant).forms.filter(item => !item.deleted_at)) {
    const id = organisationOfForm(tenant, form).id
    forms.set(id, (forms.get(id) ?? 0) + 1)
    responses.set(id, (responses.get(id) ?? 0) + form.responses_count)
  }
  return (item: StoredOrganisation): Organisation => ({ ...item, forms_count: forms.get(item.id) ?? 0, responses_count: responses.get(item.id) ?? 0 })
}
const audit = (event: H3Event, tenant: MockTenant, user: MockUser, item: StoredOrganisation, changes: { field: string; before: string | null; after: string | null }[]) =>
  recordAudit(event, tenant, { action: 'settings.updated', actor: actorOf(user), resource: { type: 'organisation', id: item.id, name: item.name }, changes })

export const listOrganisations = defineMockRoute(({ event }) => {
  const { tenant } = requireAuth(event)
  const view = counts(tenant)
  return ok(organisationsOf(tenant).map(view).sort((a, b) => Number(b.main) - Number(a.main) || a.name.localeCompare(b.name)))
})

const optional = (max: number) => z.string().trim().max(max).nullable().transform(value => value || null)
const saveSchema = z.object({
  name: z.string().trim().min(2).max(120),
  short_name: optional(24),
  website: optional(200).refine(value => !value || /^https?:\/\/[^\s.]+\.[^\s]+$/i.test(value), 'website'),
  logo_upload_id: z.string().max(100).nullable().optional(),
})

function nameFree(tenant: MockTenant, name: string, except?: string) {
  if (organisationsOf(tenant).some(item => item.id !== except && item.name.toLowerCase() === name.toLowerCase())) throw new MockError('FRM-ORG-1001', [{ field: 'name', message: 'taken' }])
}
function logo(tenant: MockTenant, id: string | null | undefined, current: string | null) {
  if (id === undefined) return current
  if (id === null) return null
  const url = completedUploadUrl(id, tenant.id)
  if (!url) throw new MockError('FRM-GEN-1002', [{ field: 'logo', message: 'upload_again' }])
  return url
}

export const createOrganisation = defineMockRoute(({ event, body }) => {
  const { tenant, user } = requireAdmin(event)
  const input = parseBody(saveSchema, body)
  nameFree(tenant, input.name)
  const at = new Date().toISOString()
  const item: StoredOrganisation = { id: crypto.randomUUID(), name: input.name, short_name: input.short_name, website: input.website, logo_url: logo(tenant, input.logo_upload_id, null), main: false, status: 'active', created_at: at, updated_at: at }
  organisationsOf(tenant).push(item)
  saveOrganisations()
  audit(event, tenant, user, item, [{ field: 'organisation', before: null, after: item.name }])
  return ok(counts(tenant)(item), {}, 201)
})

const find = (tenant: MockTenant, id: string | undefined) => {
  const item = organisationsOf(tenant).find(org => org.id === id)
  if (!item) throw new MockError('FRM-GEN-1004')
  return item
}

export const updateOrganisation = defineMockRoute(({ event, body }) => {
  const { tenant, user } = requireAdmin(event)
  const item = find(tenant, getRouterParam(event, 'id'))
  const input = parseBody(saveSchema, body)
  nameFree(tenant, input.name, item.id)
  const changes: { field: string; before: string | null; after: string | null }[] = (['name', 'short_name', 'website'] as const).filter(key => item[key] !== input[key]).map(key => ({ field: key, before: item[key], after: input[key] }))
  const nextLogo = logo(tenant, input.logo_upload_id, item.logo_url)
  if (nextLogo !== item.logo_url) changes.push({ field: 'logo', before: item.logo_url ? 'set' : null, after: nextLogo ? 'uploaded' : 'removed' })
  Object.assign(item, { name: input.name, short_name: input.short_name, website: input.website, logo_url: nextLogo, updated_at: new Date().toISOString() })
  // The main one is the workspace's own name too
  if (item.main) tenant.organisation.name = item.name
  saveOrganisations()
  if (changes.length) audit(event, tenant, user, item, changes)
  return ok(counts(tenant)(item))
})

const setStatus = (status: 'active' | 'archived') =>
  defineMockRoute(({ event }) => {
    const { tenant, user } = requireAdmin(event)
    const item = find(tenant, getRouterParam(event, 'id'))
    if (item.main && status === 'archived') throw new MockError('FRM-ORG-1003')
    if (item.status !== status) {
      audit(event, tenant, user, item, [{ field: 'status', before: item.status, after: status }])
      item.status = status
      item.updated_at = new Date().toISOString()
      saveOrganisations()
    }
    return ok(counts(tenant)(item))
  })
export const archiveOrganisation = setStatus('archived')
export const restoreOrganisation = setStatus('active')

const moveSchema = z.object({ organisation_id: z.string().max(64) })

export const moveForm = defineMockRoute(({ event, body }) => {
  const { tenant, user } = requireAuth(event)
  const form = formsOf(tenant).forms.find(item => item.id === getRouterParam(event, 'id') && !item.deleted_at)
  if (!form) throw new MockError('FRM-GEN-1004')
  requireLevel(form, user, 'edit')
  const { organisation_id } = parseBody(moveSchema, body)
  const target = find(tenant, organisation_id)
  if (target.status !== 'active') throw new MockError('FRM-GEN-1002', [{ field: 'organisation_id', message: 'archived' }])
  const before = organisationOfForm(tenant, form)
  form.organisation_id = target.main ? null : target.id
  saveForms()
  if (before.id !== target.id) recordAudit(event, tenant, { action: 'forms.updated', actor: actorOf(user), resource: { type: 'form', id: form.id, name: form.name }, changes: [{ field: 'organisation', before: before.name, after: target.name }] })
  return ok(summaryOf(form))
})

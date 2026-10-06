/**
 * Workspace settings (F14, docs/API-CONTRACT.md → Settings). Admins only, except the workspace's
 * language and region, which every member's portal needs to show dates and numbers.
 *
 *   GET   /settings                  every section, with who changed it last
 *   GET   /settings/localisation     any member
 *   GET   /settings/:section         company · branding · localisation
 *   PATCH /settings/:section         the whole section (branding: upload ids for pictures) → the section
 *
 * Every change is in the audit trail (`settings.updated`, field by field).
 */
import type { BrandingSettings, SettingsSection } from '#shared/types/settings'
import { SETTINGS_SECTIONS } from '#shared/types/settings'
import { brandingSchema, companySchema, localisationSchema } from '#shared/utils/settings/schemas'
import { actorOf, recordAudit } from '../core/audit'
import { requireAdmin, requireAuth } from '../core/auth'
import { MockError, ok } from '../core/respond'
import { defineMockRoute } from '../core/route'
import { parseBody } from '../core/validate'
import { settingsChanges, settingsOf, writeSettings } from '../data/settingsStore'
import type { MockTenant } from '../data/tenants'
import { completedUploadUrl } from './uploads'

const LABELS: Record<SettingsSection, string> = { company: 'Company', branding: 'Branding', localisation: 'Language and region' }

function sectionOf(value: string | undefined): SettingsSection {
  if (!value || !(SETTINGS_SECTIONS as readonly string[]).includes(value)) throw new MockError('FRM-GEN-1004')
  return value as SettingsSection
}

export const getSettings = defineMockRoute(({ event }) => {
  const { tenant } = requireAdmin(event)
  return ok(settingsOf(tenant))
})

export const getLocalisation = defineMockRoute(({ event }) => {
  const { tenant } = requireAuth(event)
  return ok(settingsOf(tenant).localisation)
})

export const getSection = defineMockRoute(({ event }) => {
  const { tenant } = requireAdmin(event)
  return ok(settingsOf(tenant)[sectionOf(getRouterParam(event, 'section'))])
})

/** An upload id becomes its file address; null removes the picture; left out keeps it. */
function picture(tenant: MockTenant, field: string, id: string | null | undefined, current: string | null): string | null {
  if (id === undefined) return current
  if (id === null) return null
  const url = completedUploadUrl(id, tenant.id)
  if (!url) throw new MockError('FRM-GEN-1002', [{ field, message: 'upload_again' }])
  return url
}

export const patchSection = defineMockRoute(({ event, body }) => {
  const { tenant, user } = requireAdmin(event)
  const section = sectionOf(getRouterParam(event, 'section') ?? event.path.split('?')[0]!.split('/').pop())
  const settings = settingsOf(tenant)
  const by = `${user.first_name} ${user.last_name}`
  let next: unknown
  let changes: ReturnType<typeof settingsChanges>
  if (section === 'branding') {
    const values = parseBody(brandingSchema, body)
    const before = settings.branding
    const value: BrandingSettings = {
      logo_url: picture(tenant, 'logo', values.logo_upload_id, before.logo_url),
      logo_dark_url: picture(tenant, 'logo_dark', values.logo_dark_upload_id, before.logo_dark_url),
      favicon_url: picture(tenant, 'favicon', values.favicon_upload_id, before.favicon_url),
      signin_image_url: picture(tenant, 'signin_image', values.signin_image_upload_id, before.signin_image_url),
      brand_color: values.brand_color ? values.brand_color.toUpperCase() : null,
      signin_message: values.signin_message,
    }
    // Pictures by what happened to them, never their addresses
    const pictureChange = (field: keyof BrandingSettings, a: string | null, b: string | null) => (a === b ? [] : [{ field, before: a ? 'set' : null, after: b ? (a ? 'replaced' : 'uploaded') : 'removed' }])
    changes = [
      ...pictureChange('logo_url', before.logo_url, value.logo_url),
      ...pictureChange('logo_dark_url', before.logo_dark_url, value.logo_dark_url),
      ...pictureChange('favicon_url', before.favicon_url, value.favicon_url),
      ...pictureChange('signin_image_url', before.signin_image_url, value.signin_image_url),
      ...settingsChanges({ brand_color: before.brand_color, signin_message: before.signin_message }, { brand_color: value.brand_color, signin_message: value.signin_message }),
    ]
    next = writeSettings(tenant, 'branding', value, by).branding
  } else if (section === 'company') {
    const value = parseBody(companySchema, body)
    changes = settingsChanges(settings.company as unknown as Record<string, unknown>, value as unknown as Record<string, unknown>)
    next = writeSettings(tenant, 'company', value, by).company
  } else {
    const value = parseBody(localisationSchema, body)
    changes = settingsChanges(settings.localisation as unknown as Record<string, unknown>, value as unknown as Record<string, unknown>)
    next = writeSettings(tenant, 'localisation', value, by).localisation
  }
  if (changes.length) recordAudit(event, tenant, { action: 'settings.updated', actor: actorOf(user), resource: { type: 'setting', id: null, name: LABELS[section] }, changes })
  return ok(next)
})

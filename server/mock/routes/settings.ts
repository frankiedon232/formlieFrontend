/**
 * Workspace settings (F14, docs/API-CONTRACT.md → Settings). Admins only, except the workspace's
 * language and region, which every member's portal needs to show dates and numbers.
 *
 *   GET   /settings                  every section, with who changed it last
 *   GET   /settings/localisation     any member
 *   GET   /settings/:section         company · branding · localisation
 *   PATCH /settings/:section         the whole section (branding: upload ids for pictures) → the section
 *   GET   /settings/security/sessions             who is signed in (F14 M3)
 *   POST  /settings/security/sessions/sign-out    { ids } or { everyone_else: true }
 *   GET   /settings/security/activity             sign-in activity of the last 14 days, and the caller's address
 *
 * Sign-in and security refuse a change that would lock the admin out (FRM-AUTH-1017): their own email
 * domain left off the allowed domains, or their own address left off the IP allowlist.
 * Every change is in the audit trail (`settings.updated`, field by field).
 */
import { z } from 'zod'
import type { BrandingSettings, SecurityActivity, SettingsSection } from '#shared/types/settings'
import { SETTINGS_SECTIONS } from '#shared/types/settings'
import { ipInCidr } from '#shared/utils/apiService/access'
import { brandingSchema, companySchema, localisationSchema, securitySchema, signinSchema } from '#shared/utils/settings/schemas'
import { actorOf, auditLogOf, recordAudit } from '../core/audit'
import { activeSessions, callerIp, currentSessionId, requireAdmin, requireAuth, revokeSessions } from '../core/auth'
import { MockError, ok } from '../core/respond'
import { defineMockRoute } from '../core/route'
import { parseBody } from '../core/validate'
import { settingsChanges, settingsOf, writeSettings } from '../data/settingsStore'
import type { MockTenant } from '../data/tenants'
import { completedUploadUrl } from './uploads'

const LABELS: Record<SettingsSection, string> = { company: 'Company', branding: 'Branding', localisation: 'Language and region', signin: 'Sign-in', security: 'Security' }
const lockedOut = (field: string, message: string) => new MockError('FRM-AUTH-1017', [{ field, message }])

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
  return ok(settingsOf(tenant)[sectionOf(getRouterParam(event, 'section') ?? event.path.split('?')[0]!.split('/').pop())])
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
  } else if (section === 'signin') {
    const value = parseBody(signinSchema, body)
    const domain = user.email.split('@').pop()!.toLowerCase()
    if (value.allowed_domains.length && !value.allowed_domains.some(item => domain === item || domain.endsWith(`.${item}`))) throw lockedOut('allowed_domains', 'own_domain')
    changes = settingsChanges(settings.signin as unknown as Record<string, unknown>, value as unknown as Record<string, unknown>)
    next = writeSettings(tenant, 'signin', value, by).signin
  } else if (section === 'security') {
    const value = parseBody(securitySchema, body)
    if (value.ip_allowlist.enabled && !value.ip_allowlist.entries.some(entry => ipInCidr(callerIp(event), entry.value))) throw lockedOut('ip_allowlist', 'own_ip')
    // The allowlist by its addresses in the audit trail
    const flat = (item: typeof value) => ({ ...item, ip_allowlist: { enabled: item.ip_allowlist.enabled, entries: item.ip_allowlist.entries.map(entry => (entry.label ? `${entry.value} (${entry.label})` : entry.value)) } })
    changes = settingsChanges(flat(settings.security) as unknown as Record<string, unknown>, flat(value) as unknown as Record<string, unknown>)
    next = writeSettings(tenant, 'security', value, by).security
  } else {
    const value = parseBody(localisationSchema, body)
    changes = settingsChanges(settings.localisation as unknown as Record<string, unknown>, value as unknown as Record<string, unknown>)
    next = writeSettings(tenant, 'localisation', value, by).localisation
  }
  if (changes.length) recordAudit(event, tenant, { action: 'settings.updated', actor: actorOf(user), resource: { type: 'setting', id: null, name: LABELS[section] }, changes })
  return ok(next)
})

// ── Security: sessions and sign-in activity (F14 M3) ─────────────────────────────────

export const listSessions = defineMockRoute(({ event }) => {
  const { tenant } = requireAdmin(event)
  return ok(activeSessions(event, tenant))
})

const signOutSchema = z.union([z.object({ ids: z.array(z.string().max(64)).min(1).max(500) }), z.object({ everyone_else: z.literal(true) })])

/** Ends the chosen sessions, or everyone's but the caller's (never the caller's own). */
export const signOutSessions = defineMockRoute(({ event, body }) => {
  const { tenant, user } = requireAdmin(event)
  const input = parseBody(signOutSchema, body)
  const keep = currentSessionId(event)
  const ended = revokeSessions(tenant, { ids: 'ids' in input ? input.ids : undefined, keep })
  if (ended.length)
    recordAudit(event, tenant, {
      action: 'auth.session.revoked',
      actor: actorOf(user),
      resource: { type: 'session', id: null, name: ended.length === 1 ? `${ended[0]!.user.first_name} ${ended[0]!.user.last_name}` : `${ended.length} sessions` },
      metadata: { cause: 'everyone_else' in input ? 'signed_out_everyone' : 'signed_out_by_admin', sessions: String(ended.length) },
    })
  return ok({ signed_out: ended.length })
})

const SIGNIN_ACTIONS = new Set(['auth.login.succeeded', 'auth.login.failed', 'auth.login.blocked', 'auth.otp.failed', 'auth.otp.locked'])

export const securityActivity = defineMockRoute(({ event }) => {
  const { tenant } = requireAdmin(event)
  const since = Date.now() - 14 * 86_400_000
  const events = auditLogOf(tenant).filter(item => SIGNIN_ACTIONS.has(item.action) && Date.parse(item.occurred_at) >= since)
  const days = Array.from({ length: 14 }, (_, i) => ({ date: new Date(since + (i + 1) * 86_400_000).toISOString().slice(0, 10), succeeded: 0, failed: 0 }))
  const totals = { succeeded: 0, failed: 0, blocked: 0, locked: 0 }
  for (const item of events) {
    const day = days.find(entry => entry.date === item.occurred_at.slice(0, 10))
    if (item.action === 'auth.login.succeeded') {
      totals.succeeded++
      if (day) day.succeeded++
      continue
    }
    if (item.action === 'auth.login.blocked') totals.blocked++
    else if (item.action === 'auth.otp.locked') totals.locked++
    else totals.failed++
    if (day) day.failed++
  }
  return ok<SecurityActivity>({
    my_ip: callerIp(event),
    days,
    totals,
    recent: events.slice(0, 8).map(item => ({ id: item.id, at: item.occurred_at, action: item.action, outcome: item.outcome, name: item.actor.name, email: item.actor.email, ip: item.location.ip.replace(/^::ffff:/i, ''), reason: item.reason })),
  })
})

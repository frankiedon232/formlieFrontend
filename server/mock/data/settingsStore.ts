/**
 * Workspace settings in the mock (F14), kept in `.data/mock/settings.json`: one record per workspace
 * with company, branding and localisation. Onboarding reads and writes the same record, and the
 * workspace's public profile (sign-in page, public forms) is built from it.
 */
import type { NotificationSettings } from '#shared/types/notifications'
import type { FormDefaults, PrivacySettings } from '#shared/types/privacy'
import type { SecuritySettings, SettingsChange, SettingsSection, SigninSettings, WorkspaceSettings } from '#shared/types/settings'
import { FORMALIE_APPEARANCE } from '#shared/types/appearance'
import { DEFAULT_PASSWORD_POLICY } from '#shared/utils/auth/password'
import { APP_LOCALES } from '#shared/utils/i18n/locales'
import { loadPersisted, savePersisted } from '../core/persist'
import type { MockTenant } from './tenants'

const stores = new Map<string, WorkspaceSettings>(Object.entries(loadPersisted<Record<string, WorkspaceSettings>>('settings', {})))
export const saveSettings = () => savePersisted('settings', () => Object.fromEntries(stores))

/** Sign-in and security start from the workspace's methods and Formalie's defaults (F14 M3); codes by email, text messages only when switched on (owner, 2026-10-07). */
const seedSignin = (tenant: MockTenant): SigninSettings => ({ methods: [...tenant.auth_providers], code: { sms: false, expiry_minutes: 5, max_attempts: 5 }, allowed_domains: [] })
const seedSecurity = (): SecuritySettings => ({
  password: { ...DEFAULT_PASSWORD_POLICY, reuse_last: 0, expiry_days: 0 },
  sessions: { idle_minutes: 60, max_hours: 168 },
  ip_allowlist: { enabled: false, entries: [] },
})

/** Notifications (F14 M4): responses in the app for everyone, problems also by email to admins. */
const seedNotifications = (): NotificationSettings => {
  const rule = (in_app: boolean, email: boolean, to: 'admins' | 'everyone' = 'admins') => ({ in_app, email, to, people: [] })
  return {
    events: {
      response_new: rule(true, false, 'everyone'),
      response_duplicate: rule(true, false),
      form_limit: rule(true, true),
      form_closing: rule(true, true),
      export_ready: rule(true, false),
      webhook_failing: rule(true, true),
      security_alert: rule(true, true),
    },
    digest: { enabled: false, hour: 8 },
  }
}

/** Privacy and form defaults (F14 M5): keep responses, no notice or consent line until set; forms as they start today. */
const seedPrivacy = (): PrivacySettings => ({ retention_days: 0, notice_url: null, consent: false, consent_text: null })
const seedFormDefaults = (): FormDefaults => ({ settings: { progress_bar: true, save_resume: false, field_icons: true, label_position: 'top' }, theme_id: null, thank_you: { title: null, message: null }, team_emails: [], embed_domains: [] })

function seed(tenant: MockTenant): WorkspaceSettings {
  return {
    company: {
      legal_name: tenant.organisation.name,
      display_name: tenant.organisation.name,
      industry: null,
      size: null,
      website: tenant.website ?? null,
      registration_number: null,
      tax_number: null,
      support_email: null,
      support_phone: null,
      address: { line1: null, line2: null, city: null, region: null, postal_code: null, country: null },
    },
    branding: { logo_url: tenant.logo_url ?? null, logo_dark_url: null, favicon_url: null, brand_color: tenant.brand_color ?? null, signin_message: null },
    localisation: { language: 'en', timezone: 'UTC', currency: 'USD', date_format: 'DD/MM/YYYY', number_format: '1,234.56', week_start: 'monday', form_languages: APP_LOCALES.map(item => item.code) },
    signin: seedSignin(tenant),
    security: seedSecurity(),
    notifications: seedNotifications(),
    emails: { sender_name: null, reply_to: null, footer: null, custom: {} },
    privacy: seedPrivacy(),
    form_defaults: seedFormDefaults(),
    appearance: structuredClone(FORMALIE_APPEARANCE),
    updated: { company: null, branding: null, localisation: null, signin: null, security: null, notifications: null, emails: null, privacy: null, form_defaults: null, appearance: null },
  }
}

export function settingsOf(tenant: MockTenant): WorkspaceSettings {
  let settings = stores.get(tenant.id)
  if (!settings) {
    settings = seed(tenant)
    stores.set(tenant.id, settings)
    saveSettings()
  } else if (!settings.signin || !settings.security || !settings.notifications || !settings.emails || !settings.privacy || !settings.form_defaults || !settings.appearance) {
    // Saved before these sections existed (F14 M3, M4)
    settings.signin ??= seedSignin(tenant)
    settings.security ??= seedSecurity()
    settings.notifications ??= seedNotifications()
    settings.emails ??= { sender_name: null, reply_to: null, footer: null, custom: {} }
    settings.updated.emails ??= null
    settings.privacy ??= seedPrivacy()
    settings.form_defaults ??= seedFormDefaults()
    settings.updated.privacy ??= null
    settings.updated.form_defaults ??= null
    settings.appearance ??= structuredClone(FORMALIE_APPEARANCE)
    settings.updated.appearance ??= null
    settings.updated.signin ??= null
    settings.updated.security ??= null
    settings.updated.notifications ??= null
    saveSettings()
  }
  // Appearance saved before light / dark (leftovers L3)
  if (settings.appearance && (settings.appearance.default_mode === undefined || settings.appearance.dark === undefined)) {
    settings.appearance.default_mode ??= 'system'
    settings.appearance.dark ??= null
    saveSettings()
  }
  // The sign-in methods live here; the workspace record follows them
  tenant.auth_providers = [...settings.signin.methods]
  return settings
}

/** Saves a section and keeps the workspace's own fields (name, logo, colour, website) in step. */
export function writeSettings<S extends SettingsSection>(tenant: MockTenant, section: S, value: WorkspaceSettings[S], by: SettingsChange['by']) {
  const settings = settingsOf(tenant)
  settings[section] = value
  settings.updated[section] = { at: new Date().toISOString(), by }
  if (section === 'company') {
    tenant.organisation.name = settings.company.display_name
    tenant.website = settings.company.website
  }
  if (section === 'branding') {
    tenant.logo_url = settings.branding.logo_url
    tenant.brand_color = settings.branding.brand_color
  }
  saveSettings()
  return settings
}

/** Field-level before / after for the audit trail (nested objects by their own fields). */
export function settingsChanges(before: Record<string, unknown>, after: Record<string, unknown>, prefix = ''): { field: string; before: string | null; after: string | null }[] {
  return Object.keys(after).flatMap(key => {
    const a = before[key]
    const b = after[key]
    if (b && typeof b === 'object' && !Array.isArray(b)) return settingsChanges((a ?? {}) as Record<string, unknown>, b as Record<string, unknown>, `${prefix}${key}.`)
    const show = (value: unknown) => (value == null || value === '' ? null : Array.isArray(value) ? value.join(', ') : String(value))
    return show(a) === show(b) ? [] : [{ field: `${prefix}${key}`, before: show(a), after: show(b) }]
  })
}

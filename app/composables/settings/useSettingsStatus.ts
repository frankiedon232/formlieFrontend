/**
 * How far each Settings section is (F14 overview): a one-line status per section, the workspace's
 * setup as a share, and the next step worth taking. Built from the loaded settings only.
 */
import type { WorkspaceSettings } from '#shared/types/settings'
import { APP_LOCALES } from '#shared/utils/i18n/locales'

export interface SectionStatus {
  text: string
  /** done: all set · partial: some · todo: nothing yet · info: a summary, nothing to finish */
  tone: 'done' | 'partial' | 'todo' | 'info'
}

export function useSettingsStatus(settings: Ref<WorkspaceSettings | null>) {
  const { t } = useI18n()
  const { counts } = useNavCounts()
  const tenant = useTenant()
  const config = useRuntimeConfig()

  const company = computed(() => {
    const c = settings.value?.company
    if (!c) return { done: 0, total: 8 }
    const fields = [c.legal_name, c.display_name, c.industry, c.size, c.website, c.support_email, c.address.country, c.registration_number]
    return { done: fields.filter(Boolean).length, total: fields.length }
  })
  const branding = computed(() => {
    const b = settings.value?.branding
    if (!b) return { done: 0, total: 4 }
    // The sign-in picture is gone (owner 2026-10-10): logo, colour, tab icon and welcome make it complete
    const fields = [b.logo_url, b.brand_color, b.favicon_url, b.signin_message]
    return { done: fields.filter(Boolean).length, total: fields.length }
  })
  const languageChecked = computed(() => !!settings.value?.updated.localisation)

  const count = (part: { done: number; total: number }, key: string): SectionStatus =>
    part.done === part.total ? { text: t('settings.status.complete'), tone: 'done' } : { text: t(`settings.status.${key}`, { n: part.done, total: part.total }), tone: part.done ? 'partial' : 'todo' }

  const statusOf = (key: string): SectionStatus | null => {
    const s = settings.value
    if (!s) return null
    if (key === 'company') return count(company.value, 'details')
    if (key === 'branding') return count(branding.value, 'set')
    if (key === 'language') {
      const name = APP_LOCALES.find(item => item.code === s.localisation.language)?.name ?? s.localisation.language
      return { text: `${name} · ${s.localisation.timezone} · ${s.localisation.currency}`, tone: languageChecked.value ? 'done' : 'partial' }
    }
    if (key === 'signin') {
      const ways = s.signin.methods.length
      return { text: t('settings.status.signin', { n: ways }, ways) + (s.signin.allowed_domains.length ? ` · ${s.signin.allowed_domains.join(', ')}` : ''), tone: 'info' }
    }
    if (key === 'security') {
      const idle = s.security.sessions.idle_minutes
      const text = idle < 60 ? t('settings.status.idleMinutes', { n: idle }) : t('settings.status.idleHours', { n: idle / 60 }, idle / 60)
      return { text: s.security.ip_allowlist.enabled ? `${text} · ${t('settings.status.allowlist')}` : text, tone: 'info' }
    }
    if (key === 'address') return { text: `${tenant.profile.value?.subdomain ?? ''}.${config.public.rootDomain}`, tone: 'info' }
    if (key === 'appearance') return { text: s.appearance.preset === 'custom' ? t('settings.status.customLook') : t(`settings.appearance.preset.${s.appearance.preset}`), tone: 'info' }
    if (key === 'privacy') {
      const days = s.privacy.retention_days
      return { text: (days ? t('settings.status.keepDays', { n: days }, days) : t('settings.status.keepAll')) + (s.privacy.notice_url ? ` · ${t('settings.status.notice')}` : ''), tone: s.privacy.notice_url ? 'done' : 'partial' }
    }
    if (key === 'formDefaults') return { text: s.form_defaults.theme_id ? t('settings.status.withTheme') : t('settings.status.workspaceLook'), tone: 'info' }
    if (key === 'emails') {
      const own = Object.values(s.emails.custom).reduce((sum, langs) => sum + Object.keys(langs ?? {}).length, 0)
      return { text: (s.emails.sender_name || s.company.display_name) + (own ? ` · ${t('settings.status.ownTexts', { n: own }, own)}` : ''), tone: 'info' }
    }
    if (key === 'notifications') {
      const on = Object.values(s.notifications.events).filter(rule => rule.in_app || rule.email).length
      return { text: t('settings.status.notifications', { n: on, total: Object.keys(s.notifications.events).length }) + (s.notifications.digest.enabled ? ` · ${t('settings.status.digest')}` : ''), tone: 'info' }
    }
    if (key === 'themes' && counts.value) return { text: t('settings.status.themes', { n: counts.value.themes.total }, counts.value.themes.total), tone: 'info' }
    if (key === 'landingPages' && counts.value) return { text: t('settings.status.pages', { n: counts.value.pages.total }, counts.value.pages.total), tone: 'info' }
    return null
  }

  /** The workspace's setup: company details, branding and a checked language and region, equally weighted. */
  const setup = computed(() => Math.round(((company.value.done / company.value.total + branding.value.done / branding.value.total + (languageChecked.value ? 1 : 0)) / 3) * 100))

  /** The most useful next step, or null when everything is done. */
  const next = computed(() => {
    const s = settings.value
    if (!s) return null
    if (company.value.done < company.value.total) return { key: 'company', to: '/settings/company', icon: 'i-lucide-building-2' }
    if (!s.branding.logo_url) return { key: 'logo', to: '/settings/branding', icon: 'i-lucide-image' }
    if (!languageChecked.value) return { key: 'language', to: '/settings/language', icon: 'i-lucide-languages' }
    if (branding.value.done < branding.value.total) return { key: 'branding', to: '/settings/branding', icon: 'i-lucide-badge-check' }
    return null
  })

  return { statusOf, setup, next }
}

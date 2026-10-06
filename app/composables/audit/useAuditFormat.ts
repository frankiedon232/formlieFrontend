import type { BadgeProps } from '@nuxt/ui'
import type { AuditChange, AuditDevice, AuditEvent, AuditOutcome } from '#shared/types/audit'
import { AUDIT_EVENTS, auditActionKey } from '#shared/utils/audit/events'

const OUTCOME_COLORS: Record<AuditOutcome, BadgeProps['color']> = {
  success: 'success',
  failure: 'warning',
  blocked: 'error',
}

/** Square bullet colours for the outcome filter (same style as the sidebar). */
export const OUTCOME_DOTS: Record<AuditOutcome, string> = {
  success: 'bg-green-500',
  failure: 'bg-amber-500',
  blocked: 'bg-red-500',
}

/** Where an item lives in the portal (until each item gets its own page). */
const RESOURCE_PAGES: Record<string, (resource: NonNullable<AuditEvent['resource']>) => string> = {
  form: resource => `/forms?q=${encodeURIComponent(resource.name ?? '')}`,
  setting: () => '/settings',
  workspace: () => '/settings',
  destination: () => '/data-sources/destinations',
  webhook: () => '/api-service/webhooks',
  api_key: () => '/api-service/auth',
}

const DEVICE_ICONS: Record<AuditDevice['type'], string> = {
  desktop: 'i-lucide-monitor',
  mobile: 'i-lucide-smartphone',
  tablet: 'i-lucide-tablet',
  unknown: 'i-lucide-circle-help',
}

/** Translated labels, icons and colours for audit events (one place for the page, cards and timeline). */
export function useAuditFormat() {
  const { t, te } = useI18n()
  const { current } = useAppLocale()

  const actionLabel = (action: string) => {
    const key = `audit.action.${auditActionKey(action)}`
    return te(key) ? t(key) : action
  }
  const actionIcon = (action: string) =>
    (AUDIT_EVENTS as Record<string, { icon: string }>)[action]?.icon ?? 'i-lucide-activity'
  const areaLabel = (area: string) => (te(`audit.area.${area}`) ? t(`audit.area.${area}`) : area)
  const outcomeLabel = (outcome: AuditOutcome) => t(`audit.outcome.${outcome}`)
  const outcomeColor = (outcome: AuditOutcome) => OUTCOME_COLORS[outcome]
  const resourceType = (type: string) => (te(`audit.resource.${type}`) ? t(`audit.resource.${type}`) : type)
  const fieldLabel = (field: string) =>
    te(`audit.field.${field}`) ? t(`audit.field.${field}`) : field.replace(/_/g, ' ')

  function countryName(code: string | null) {
    if (!code) return ''
    try {
      return new Intl.DisplayNames([current.value.language], { type: 'region' }).of(code) ?? code
    } catch {
      return code
    }
  }
  const countryFlag = (code: string | null) => (code ? `i-circle-flags-${code.toLowerCase()}` : '')

  function place(event: AuditEvent) {
    const { city, country } = event.location
    if (!city && !country) return t('audit.unknownLocation')
    return [city, countryName(country)].filter(Boolean).join(', ')
  }

  const deviceIcon = (device: AuditDevice) => DEVICE_ICONS[device.type]
  function deviceLabel(device: AuditDevice) {
    const parts = [device.browser, device.os].filter(Boolean)
    return parts.length ? parts.join(' · ') : t(`audit.device.${device.type}`)
  }

  function changeValue(value: AuditChange['before']) {
    if (value === null || value === '') return t('audit.detail.empty')
    if (typeof value === 'boolean') return value ? t('audit.yes') : t('audit.no')
    return String(value)
  }

  /** "Not signed in" for attempts by someone we could not identify. */
  const actorDescription = (event: AuditEvent) =>
    event.actor.id ? (event.actor.email ?? t(`audit.actorType.${event.actor.type}`)) : t('audit.notSignedIn')

  const resourceLink = (resource: AuditEvent['resource']) =>
    resource?.name ? (RESOURCE_PAGES[resource.type]?.(resource) ?? null) : null

  return {
    resourceLink,
    actionLabel,
    actionIcon,
    areaLabel,
    outcomeLabel,
    outcomeColor,
    resourceType,
    fieldLabel,
    countryName,
    countryFlag,
    place,
    deviceIcon,
    deviceLabel,
    changeValue,
    actorDescription,
  }
}

/**
 * Every Settings section (F14), grouped like the navigator shows them. Live ones have a page; the
 * rest are marked "soon" with the milestone that brings them, so the whole plan is visible without
 * dead ends (soon items are not links). One list for the navigator, the overview and search.
 */
export interface SettingsSectionItem {
  key: string
  icon: string
  /** Its page; absent while it is still to come. */
  to?: string
  /** The milestone that brings it, while it is still to come. */
  soon?: string
}
export interface SettingsGroup {
  key: string
  items: SettingsSectionItem[]
}

const GROUPS: SettingsGroup[] = [
  {
    key: 'workspace',
    items: [
      { key: 'overview', icon: 'i-lucide-layout-dashboard', to: '/settings' },
      { key: 'company', icon: 'i-lucide-building-2', to: '/settings/company' },
      { key: 'branding', icon: 'i-lucide-badge-check', to: '/settings/branding' },
      { key: 'language', icon: 'i-lucide-languages', to: '/settings/language' },
      { key: 'appearance', icon: 'i-lucide-palette', soon: 'M6' },
      { key: 'address', icon: 'i-lucide-globe', soon: 'M7' },
    ],
  },
  {
    key: 'organisation',
    items: [
      { key: 'departments', icon: 'i-lucide-network', to: '/settings/departments' },
      { key: 'jobTitles', icon: 'i-lucide-id-card', to: '/settings/job-titles' },
      { key: 'places', icon: 'i-lucide-map-pin', to: '/settings/places' },
      { key: 'lists', icon: 'i-lucide-list-tree', to: '/option-sets' },
    ],
  },
  {
    key: 'access',
    items: [
      { key: 'signin', icon: 'i-lucide-log-in', to: '/settings/signin' },
      { key: 'security', icon: 'i-lucide-shield-check', to: '/settings/security' },
    ],
  },
  {
    key: 'communication',
    items: [
      { key: 'notifications', icon: 'i-lucide-bell-ring', to: '/settings/notifications' },
      { key: 'emails', icon: 'i-lucide-mail', soon: 'M4' },
    ],
  },
  {
    key: 'data',
    items: [
      { key: 'privacy', icon: 'i-lucide-lock-keyhole', soon: 'M5' },
      { key: 'formDefaults', icon: 'i-lucide-file-cog', soon: 'M5' },
      { key: 'themes', icon: 'i-lucide-swatch-book', to: '/settings/themes' },
      { key: 'landingPages', icon: 'i-lucide-layout-template', to: '/settings/landing-pages' },
    ],
  },
]

export function useSettingsSections() {
  const { t } = useI18n()
  const route = useRoute()
  const label = (item: SettingsSectionItem) => t(`settings.nav.${item.key}`)
  const description = (item: SettingsSectionItem) => t(`settings.desc.${item.key}`)
  /** The section the page belongs to (overview only on /settings itself). */
  const current = computed(() => GROUPS.flatMap(group => group.items).find(item => item.to && (item.to === '/settings' ? route.path === '/settings' : route.path === item.to || route.path.startsWith(`${item.to}/`))) ?? null)
  const live = computed(() => GROUPS.flatMap(group => group.items).filter(item => item.to && item.key !== 'overview'))
  return { groups: GROUPS, label, description, current, live }
}

import type { NavigationMenuItem } from '@nuxt/ui'

export interface AppNavItem {
  /** i18n key under `nav.` */
  key: string
  icon: string
  to: string
  /** Chained shortcut, e.g. `g-f` (press G then F). */
  shortcut?: string
  children?: AppNavItem[]
}

/** Single source for the sidebar menu, command palette and go-to shortcuts. */
const MAIN_NAV: AppNavItem[] = [
  { key: 'forms', icon: 'i-lucide-file-text', to: '/forms', shortcut: 'g-f' },
  { key: 'templates', icon: 'i-lucide-layout-template', to: '/templates', shortcut: 'g-t' },
  { key: 'responses', icon: 'i-lucide-inbox', to: '/responses', shortcut: 'g-r' },
  { key: 'analytics', icon: 'i-lucide-chart-column', to: '/analytics', shortcut: 'g-a' },
  { key: 'optionSets', icon: 'i-lucide-list-checks', to: '/option-sets', shortcut: 'g-o' },
  {
    key: 'integrations',
    icon: 'i-lucide-plug',
    to: '/integrations',
    children: [
      { key: 'destinations', icon: 'i-lucide-database', to: '/integrations/destinations' },
      { key: 'webhooks', icon: 'i-lucide-webhook', to: '/integrations/webhooks' },
      { key: 'apiKeys', icon: 'i-lucide-key-round', to: '/integrations/api-keys' },
    ],
  },
]

const SYSTEM_NAV: AppNavItem[] = [
  { key: 'settings', icon: 'i-lucide-settings', to: '/settings', shortcut: 'g-s' },
]

export function useNavigation() {
  const { t } = useI18n()
  const route = useRoute()

  const isActive = (item: AppNavItem) => route.path === item.to || route.path.startsWith(`${item.to}/`)

  function toMenuItem(item: AppNavItem): NavigationMenuItem {
    return {
      label: t(`nav.${item.key}`),
      icon: item.icon,
      to: item.children ? undefined : item.to,
      active: isActive(item),
      defaultOpen: item.children ? isActive(item) : undefined,
      tooltip: { text: t(`nav.${item.key}`) },
      children: item.children?.map(toMenuItem),
    }
  }

  const mainItems = computed(() => MAIN_NAV.map(toMenuItem))
  const systemItems = computed(() => SYSTEM_NAV.map(toMenuItem))

  /** Flat list of every destination (children included), for search and shortcuts. */
  const destinations = computed(() =>
    [...MAIN_NAV, ...SYSTEM_NAV].flatMap(item => (item.children ? item.children : [item])),
  )

  return { mainItems, systemItems, destinations, isActive }
}

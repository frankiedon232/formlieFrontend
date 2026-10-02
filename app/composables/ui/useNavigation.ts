import type { BadgeProps, NavigationMenuItem } from '@nuxt/ui'
import type { NavCounts } from '#shared/types/navigation'

export interface AppNavItem {
  /** i18n key under `nav.` */
  key: string
  icon?: string
  to: string
  query?: Record<string, string>
  /** Chained shortcut, e.g. `g-f` (press G then F). */
  shortcut?: string
  /** Leading colour dot (status children) or icon colour class (resource folders). */
  dot?: string
  iconClass?: string
  children?: AppNavItem[]
  /** Badge number on the right (design: count next to the item). */
  count?: (counts: NavCounts) => number
  /** Hide the badge at 0 (e.g. "new" items); status counts always show. */
  hideZero?: boolean
  /** Workspace owners / admins only (until Roles & access, F19). */
  adminOnly?: boolean
}

/**
 * Single source for the sidebar (MAIN MENU / RESOURCES / SYSTEM), command palette and
 * go-to shortcuts. Layout follows docs/design (Screenshot 2026-10-02 084447.png).
 */
const MAIN_NAV: AppNavItem[] = [
  {
    key: 'forms',
    icon: 'i-lucide-file-text',
    to: '/forms',
    shortcut: 'g-f',
    children: [
      { key: 'formsAll', to: '/forms', dot: 'bg-(--ui-text-dimmed)', count: c => c.forms.all },
      {
        key: 'formsDraft',
        to: '/forms',
        query: { status: 'draft' },
        dot: 'bg-amber-500',
        count: c => c.forms.draft,
      },
      {
        key: 'formsPublished',
        to: '/forms',
        query: { status: 'published' },
        dot: 'bg-green-500',
        count: c => c.forms.published,
      },
      {
        key: 'formsClosed',
        to: '/forms',
        query: { status: 'closed' },
        dot: 'bg-violet-600',
        count: c => c.forms.closed,
      },
    ],
  },
  {
    key: 'responses',
    icon: 'i-lucide-inbox',
    to: '/responses',
    shortcut: 'g-r',
    count: c => c.responses.new,
    hideZero: true,
  },
  { key: 'analytics', icon: 'i-lucide-chart-column', to: '/analytics', shortcut: 'g-a' },
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

const RESOURCE_NAV: AppNavItem[] = [
  {
    key: 'templates',
    icon: 'i-lucide-folder',
    iconClass: 'text-teal-500',
    to: '/templates',
    shortcut: 'g-t',
  },
  {
    key: 'optionSets',
    icon: 'i-lucide-folder',
    iconClass: 'text-violet-600',
    to: '/option-sets',
    shortcut: 'g-o',
  },
  { key: 'themes', icon: 'i-lucide-folder', iconClass: 'text-amber-500', to: '/settings/themes' },
]

const SYSTEM_NAV: AppNavItem[] = [
  { key: 'settings', icon: 'i-lucide-settings', to: '/settings', shortcut: 'g-s' },
  { key: 'audit', icon: 'i-lucide-scroll-text', to: '/audit', shortcut: 'g-l', adminOnly: true },
  { key: 'help', icon: 'i-lucide-circle-help', to: '/help' },
]

export function useNavigation() {
  const { t } = useI18n()
  const route = useRoute()
  const session = useSession()
  const { counts } = useNavCounts()
  const { compact } = useFormat()
  const allowed = (item: AppNavItem) => !item.adminOnly || session.user.value?.role !== 'member'

  function isActive(item: AppNavItem): boolean {
    if (item.query)
      return route.path === item.to && Object.entries(item.query).every(([k, v]) => route.query[k] === v)
    if (item.dot) return route.path === item.to && !route.query.status
    if (item.children)
      return item.children.some(isActive) || route.path.startsWith(`${item.to}/`) || route.path === item.to
    return route.path === item.to || route.path.startsWith(`${item.to}/`)
  }

  // Design: black bar on the rail border next to the active top-level item.
  // Active row = grey pill with a hairline border (design).
  const ACTIVE_BAR = [
    'after:absolute after:-start-3 after:inset-y-1 after:w-0.5 after:rounded-full after:bg-inverted',
    'before:ring before:ring-default text-highlighted',
  ].join(' ')

  // Design: small grey count on the right of the row.
  function badgeFor(item: AppNavItem): BadgeProps | undefined {
    if (!item.count || !counts.value) return undefined
    const value = item.count(counts.value)
    if (item.hideZero && !value) return undefined
    return { label: compact(value), color: 'neutral', variant: 'outline', class: 'rounded-md tabular-nums' }
  }

  function toMenuItem(item: AppNavItem, level = 0): NavigationMenuItem {
    const label = t(`nav.${item.key}`)
    const active = isActive(item)
    return {
      label,
      icon: item.icon,
      to: item.children ? undefined : { path: item.to, query: item.query },
      active,
      // Children: active = bold text only, the parent row carries the highlight (design).
      class: active
        ? level === 0
          ? ACTIVE_BAR
          : 'before:bg-transparent font-semibold text-highlighted'
        : undefined,
      defaultOpen: item.children ? active : undefined,
      tooltip: { text: label },
      slot: item.dot ? 'status' : undefined,
      badge: badgeFor(item),
      dot: item.dot,
      ui: item.iconClass ? { linkLeadingIcon: item.iconClass } : undefined,
      children: item.children?.map(child => toMenuItem(child, level + 1)),
    }
  }

  const mainItems = computed(() => MAIN_NAV.map(item => toMenuItem(item)))
  const resourceItems = computed(() => RESOURCE_NAV.map(item => toMenuItem(item)))
  const systemItems = computed(() => SYSTEM_NAV.filter(allowed).map(item => toMenuItem(item)))

  /** Flat list of top-level destinations (children with their own page included), for search, rail and shortcuts. */
  const destinations = computed(() =>
    [...MAIN_NAV, ...RESOURCE_NAV, ...SYSTEM_NAV]
      .filter(allowed)
      .flatMap(item => (item.children && !item.children[0]?.dot ? item.children : [item])),
  )

  return { mainItems, resourceItems, systemItems, destinations, isActive }
}

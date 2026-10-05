import type { BadgeProps, NavigationMenuItem } from '@nuxt/ui'
import type { NavCounts } from '#shared/types/navigation'
import { categoryOf } from '#shared/templates/categories'

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
  /** Workspace owners / admins only (until Roles & access, F22). */
  adminOnly?: boolean
  /** Active on its own path only (an overview whose sections live under it). */
  exact?: boolean
  /** Paths under this item that belong to another menu entry (e.g. themes under settings). */
  except?: string[]
  /** Paths matching this belong to another menu entry (e.g. a form's responses under Forms). */
  exceptMatch?: RegExp
  /** Paths elsewhere that belong to this entry (a form's responses open the Responses menu). */
  alsoMatch?: RegExp
  /** Text as is (data such as a template name) instead of the `nav.<key>` translation. */
  label?: string
  /** Children built from the sidebar data (recent templates / themes), before the static ones. */
  recent?: (counts: NavCounts) => AppNavItem[]
}

/**
 * Single source for the sidebar (MAIN MENU / RESOURCES / SYSTEM), command palette and
 * go-to shortcuts. Layout follows docs/design (Screenshot 2026-10-02 084447.png).
 */
/** A form's responses (`/forms/{id}/responses`) belong to the Responses menu, not Forms (owner, 2026-10-05). */
const FORM_RESPONSES = /^\/forms\/[^/]+\/responses(\/|$)/

const MAIN_NAV: AppNavItem[] = [
  {
    key: 'forms',
    icon: 'i-lucide-file-text',
    to: '/forms',
    exceptMatch: FORM_RESPONSES,
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
      {
        key: 'formsTrash',
        icon: 'i-lucide-trash-2',
        to: '/forms/trash',
        count: c => c.forms.trash,
        hideZero: true,
      },
    ],
  },
  {
    key: 'responses',
    icon: 'i-lucide-inbox',
    to: '/responses',
    alsoMatch: FORM_RESPONSES,
    shortcut: 'g-r',
    children: [
      { key: 'responsesAll', to: '/responses', dot: 'bg-(--ui-text-dimmed)', count: c => c.responses.all },
      { key: 'responsesNew', to: '/responses', query: { review: 'new' }, dot: 'bg-inverted', count: c => c.responses.new },
      { key: 'responsesReviewed', to: '/responses', query: { review: 'reviewed' }, dot: 'bg-amber-500', count: c => c.responses.reviewed },
      { key: 'responsesApproved', to: '/responses', query: { review: 'approved' }, dot: 'bg-green-500', count: c => c.responses.approved },
      { key: 'responsesRejected', to: '/responses', query: { review: 'rejected' }, dot: 'bg-red-500', count: c => c.responses.rejected },
      { key: 'responsesExports', icon: 'i-lucide-file-down', to: '/responses/exports' },
    ],
  },
  { key: 'analytics', icon: 'i-lucide-chart-column', to: '/analytics', shortcut: 'g-a' },
]

const RESOURCE_NAV: AppNavItem[] = [
  {
    key: 'templates',
    icon: 'i-lucide-layout-template',
    iconClass: 'text-teal-500',
    to: '/templates',
    shortcut: 'g-t',
    // Owner, 2026-10-03: the six most used categories, then all categories, then the workspace's own.
    recent: c =>
      c.templates.categories.slice(0, 6).map(item => ({
        key: `tplcat_${item.key}`,
        to: `/templates/category/${item.key}`,
        dot: categoryOf(item.key)?.dot,
        count: () => item.count,
      })),
    children: [
      { key: 'templatesAll', icon: 'i-lucide-shapes', to: '/templates', exact: true, count: c => c.templates.total },
      { key: 'templatesMine', icon: 'i-lucide-bookmark', to: '/templates/mine', count: c => c.templates.mine },
    ],
  },
  {
    key: 'optionSets',
    icon: 'i-lucide-folder',
    iconClass: 'text-violet-600',
    to: '/option-sets',
    shortcut: 'g-o',
  },
  {
    key: 'themes',
    icon: 'i-lucide-palette',
    iconClass: 'text-amber-500',
    to: '/settings/themes',
    // Like Templates (owner, 2026-10-03): the kinds with counts, never every saved theme.
    children: [
      { key: 'themesAll', icon: 'i-lucide-swatch-book', to: '/settings/themes', exact: true, count: c => c.themes.total },
      { key: 'themesSystem', icon: 'i-lucide-sparkles', to: '/settings/themes', query: { source: 'system' }, count: c => c.themes.system },
      { key: 'themesSaved', icon: 'i-lucide-bookmark', to: '/settings/themes', query: { source: 'saved' }, count: c => c.themes.saved },
      { key: 'themesCreated', icon: 'i-lucide-paintbrush', to: '/settings/themes', query: { source: 'created' }, count: c => c.themes.created },
    ],
  },
  {
    // Page designs (owner 2026-10-04: "add more pages, just like Themes on its menu"): the page
    // around a form on its public link, the same kinds with counts.
    key: 'pages',
    icon: 'i-lucide-panels-top-left',
    iconClass: 'text-rose-500',
    to: '/settings/landing-pages',
    children: [
      { key: 'pagesAll', icon: 'i-lucide-layout-grid', to: '/settings/landing-pages', exact: true, count: c => c.pages.total },
      { key: 'pagesSystem', icon: 'i-lucide-sparkles', to: '/settings/landing-pages', query: { source: 'system' }, count: c => c.pages.system },
      { key: 'pagesSaved', icon: 'i-lucide-bookmark', to: '/settings/landing-pages', query: { source: 'saved' }, count: c => c.pages.saved },
      { key: 'pagesCreated', icon: 'i-lucide-paintbrush', to: '/settings/landing-pages', query: { source: 'created' }, count: c => c.pages.created },
    ],
  },
]

/**
 * Data sources area (F12), its own rail entry and its own menu (owner, 2026-10-02). Pages are
 * placeholders until F12; the full plan is in PROGRESS.md → F12.
 */
const DATA_NAV: AppNavItem[] = [
  { key: 'dataOverview', icon: 'i-lucide-layout-grid', to: '/data-sources', shortcut: 'g-d', exact: true },
  { key: 'dataConnections', icon: 'i-lucide-database', to: '/data-sources/connections' },
  { key: 'dataExplorer', icon: 'i-lucide-table-2', to: '/data-sources/explorer' },
  { key: 'dataQuery', icon: 'i-lucide-square-terminal', to: '/data-sources/query' },
  { key: 'dataSavedQueries', icon: 'i-lucide-bookmark', to: '/data-sources/saved-queries' },
  { key: 'destinations', icon: 'i-lucide-send', to: '/data-sources/destinations' },
  { key: 'dataTransfers', icon: 'i-lucide-arrow-left-right', to: '/data-sources/transfers' },
  { key: 'dataActivity', icon: 'i-lucide-activity', to: '/data-sources/activity' },
]

/**
 * API service area (F13, owner 2026-10-02), build API endpoints from a form so applications can
 * send and read its data. Placeholders until F13; plan in PROGRESS.md → F13.
 */
const API_NAV: AppNavItem[] = [
  { key: 'apiOverview', icon: 'i-lucide-layout-grid', to: '/api-service', shortcut: 'g-i', exact: true },
  { key: 'apiServices', icon: 'i-lucide-boxes', to: '/api-service/services' },
  { key: 'apiEndpoints', icon: 'i-lucide-route', to: '/api-service/endpoints' },
  { key: 'apiAuth', icon: 'i-lucide-key-round', to: '/api-service/auth' },
  { key: 'apiAccess', icon: 'i-lucide-shield-check', to: '/api-service/access' },
  { key: 'apiLogs', icon: 'i-lucide-scroll-text', to: '/api-service/logs' },
  { key: 'apiAnalytics', icon: 'i-lucide-chart-line', to: '/api-service/analytics' },
  { key: 'apiDocs', icon: 'i-lucide-book-open', to: '/api-service/docs' },
  // Integrations (owner, 2026-10-03: they belong to the API service).
  { key: 'webhooks', icon: 'i-lucide-webhook', to: '/api-service/webhooks' },
  { key: 'apiKeys', icon: 'i-lucide-key-round', to: '/api-service/api-keys' },
  { key: 'apiApps', icon: 'i-lucide-blocks', to: '/api-service/apps' },
]

/**
 * AI assistant area (F19, owner 2026-10-03), help creating forms and templates, analysing
 * responses and more. Placeholders until F19; plan in PROGRESS.md → F19.
 */
const AI_NAV: AppNavItem[] = [
  { key: 'aiOverview', icon: 'i-lucide-layout-grid', to: '/ai', exact: true },
  { key: 'aiCreateForm', icon: 'i-lucide-file-plus-2', to: '/ai/create-form' },
  { key: 'aiTemplates', icon: 'i-lucide-layout-template', to: '/ai/templates' },
  { key: 'aiAnalysis', icon: 'i-lucide-chart-scatter', to: '/ai/analysis' },
  { key: 'aiInsights', icon: 'i-lucide-lightbulb', to: '/ai/insights' },
  { key: 'aiTranslate', icon: 'i-lucide-languages', to: '/ai/translate' },
  { key: 'aiHistory', icon: 'i-lucide-history', to: '/ai/history' },
  { key: 'aiSettings', icon: 'i-lucide-sliders-horizontal', to: '/ai/settings' },
]

/**
 * Areas on the rail; each brings its own menu. The workspace button is the Forms area, so only
 * the extra areas are listed here.
 */
export type NavArea = 'forms' | 'data' | 'api' | 'ai'
const NAV_AREAS: { key: Exclude<NavArea, 'forms'>; label: string; icon: string; to: string; menu: AppNavItem[] }[] = [
  { key: 'data', label: 'nav.dataSources', icon: 'i-lucide-database', to: '/data-sources', menu: DATA_NAV },
  { key: 'api', label: 'nav.apiService', icon: 'i-lucide-code-xml', to: '/api-service', menu: API_NAV },
  { key: 'ai', label: 'nav.ai', icon: 'i-lucide-sparkles', to: '/ai', menu: AI_NAV },
]
const areaOf = (path: string): NavArea =>
  NAV_AREAS.find(a => path === a.to || path.startsWith(`${a.to}/`))?.key ?? 'forms'

const SYSTEM_NAV: AppNavItem[] = [
  { key: 'settings', icon: 'i-lucide-settings', to: '/settings', shortcut: 'g-s', except: ['/settings/themes'] },
  { key: 'audit', icon: 'i-lucide-scroll-text', to: '/audit', shortcut: 'g-l', adminOnly: true },
  { key: 'help', icon: 'i-lucide-circle-help', to: '/help' },
]

export function useNavigation() {
  const { t, te } = useI18n()
  const route = useRoute()
  const session = useSession()
  const { counts } = useNavCounts()
  const { compact } = useFormat()
  const allowed = (item: AppNavItem) => !item.adminOnly || session.user.value?.role !== 'member'

  function isActive(item: AppNavItem): boolean {
    if (item.except?.some(path => route.path === path || route.path.startsWith(`${path}/`))) return false
    if (item.exceptMatch?.test(route.path)) return false
    if (item.alsoMatch?.test(route.path)) return true
    if (item.query)
      return route.path === item.to && Object.entries(item.query).every(([k, v]) => route.query[k] === v)
    if (item.dot) return route.path === item.to && !route.query.status
    // "All …" entries stay unhighlighted while a single item (a search) is open.
    if (item.exact) return route.path === item.to && !route.query.q && !route.query.source
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
    const value = item.count(counts.value as NavCounts)
    if (item.hideZero && !value) return undefined
    return { label: compact(value), color: 'neutral', variant: 'outline', class: 'rounded-md tabular-nums' }
  }

  /** Static children plus the ones built from the sidebar data (recent templates / themes). */
  const childrenOf = (item: AppNavItem) =>
    item.recent && counts.value ? [...item.recent(counts.value as NavCounts), ...(item.children ?? [])] : item.children

  function toMenuItem(item: AppNavItem, level = 0): NavigationMenuItem {
    // Template categories show their translated name; other data (themes) as written.
    const templateKey = item.key.startsWith('tplcat_') ? `templates.categories.${item.key.slice(7)}` : null
    const label = templateKey && te(templateKey) ? t(templateKey) : (item.label ?? t(`nav.${item.key}`))
    const children = childrenOf(item)
    const active = isActive(item)
    return {
      label,
      // Unique across the three menu lists, so one shared value can keep a single group open.
      value: item.key,
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
      children: children?.map(child => toMenuItem(child, level + 1)),
    }
  }

  /** The rail area the current page belongs to. */
  const area = computed<NavArea>(() => areaOf(route.path))
  /** The current area's own menu (Forms: MAIN MENU + RESOURCES). */
  const areaMenu = computed(() => NAV_AREAS.find(a => a.key === area.value)?.menu)
  const mainItems = computed(() => (areaMenu.value ?? MAIN_NAV).map(item => toMenuItem(item)))
  const resourceItems = computed(() => (areaMenu.value ? [] : RESOURCE_NAV.map(item => toMenuItem(item))))
  /**
   * FOLDERS (F11 M4, owner 2026-10-02): the workspace's folders with their colour and form count, up
   * to six, then "All folders"; only in the Forms area.
   */
  const FOLDERS_SHOWN = 6
  const folderItems = computed(() => {
    if (areaMenu.value || !counts.value) return []
    const folders = (counts.value as NavCounts).folders ?? []
    const shown: AppNavItem[] = folders.slice(0, FOLDERS_SHOWN).map(folder => ({
      key: `folder_${folder.id}`,
      label: folder.name,
      icon: 'i-lucide-folder',
      iconClass: folderColor(folder.color).text,
      to: `/folders/${folder.id}`,
      count: () => folder.count,
    }))
    if (folders.length) shown.push({ key: folders.length > FOLDERS_SHOWN ? 'foldersShowAll' : 'foldersAll', icon: 'i-lucide-folders', to: '/folders', exact: true })
    return shown.map(item => toMenuItem(item))
  })
  /** Sidebar heading for the main list: the area's name, or "Main menu" for Forms. */
  const areaLabel = computed(() => NAV_AREAS.find(a => a.key === area.value)?.label ?? 'nav.main')
  const systemItems = computed(() => SYSTEM_NAV.filter(allowed).map(item => toMenuItem(item)))

  /** Flat list of top-level destinations (children with their own page included), for search, rail and shortcuts. */
  const destinations = computed(() =>
    [...MAIN_NAV, ...RESOURCE_NAV, ...DATA_NAV, ...API_NAV, ...AI_NAV, ...SYSTEM_NAV]
      .filter(allowed)
      .flatMap(item => (item.children && !item.children[0]?.dot ? item.children : [item])),
  )
  /** Collapsed rail: the current area's sections plus System. */
  const areaDestinations = computed(() =>
    [...(areaMenu.value ?? [...MAIN_NAV, ...RESOURCE_NAV]), ...SYSTEM_NAV]
      .filter(allowed)
      .flatMap(item => (item.children && !item.children[0]?.dot ? item.children : [item])),
  )

  return { mainItems, resourceItems, folderItems, systemItems, destinations, areaDestinations, area, areaLabel, areas: NAV_AREAS, isActive }
}

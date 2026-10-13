/**
 * The feature and solution pages (docs/SITEMAP.md, docs/FEATURES.md): their slugs, icons, screenshots and links.
 * The copy lives in i18n (`features.{slug}`, `solutionPages.{slug}`).
 */

export interface Screenshot {
  /** File name in public/screenshots without the extension. */
  file: string
  width: number
  height: number
  /** A `-dark` version exists for dark mode. */
  dark: boolean
}

/** The animated product demos (components/demo). */
export type DemoName = 'build' | 'design' | 'responses' | 'data' | 'api' | 'dashboard'

export interface FeaturePage {
  slug: string
  icon: string
  /** A real screen, or a drawn visual for areas without one. */
  shot?: Screenshot
  visual?: 'ai' | 'languages'
  /** An animated demo shown in the hero; the real screen then moves below the feature cards. */
  demo?: DemoName
  cardIcons: string[]
  related: string[]
}

const shot = (file: string, width: number, height: number, dark = false): Screenshot => ({
  file,
  width,
  height,
  dark,
})

export const FEATURE_PAGES: FeaturePage[] = [
  {
    slug: 'form-builder',
    demo: 'build',
    icon: 'i-lucide-layout-template',
    shot: shot('form-builder', 2320, 1800, true),
    cardIcons: [
      'i-lucide-list-checks',
      'i-lucide-rows-3',
      'i-lucide-git-branch',
      'i-lucide-calculator',
      'i-lucide-list-tree',
      'i-lucide-history',
    ],
    related: ['design', 'templates', 'languages'],
  },
  {
    slug: 'design',
    demo: 'design',
    icon: 'i-lucide-palette',
    shot: shot('form-design', 2320, 1800, true),
    cardIcons: [
      'i-lucide-swatch-book',
      'i-lucide-type',
      'i-lucide-contrast',
      'i-lucide-paintbrush',
      'i-lucide-panels-top-left',
      'i-lucide-sparkles',
    ],
    related: ['form-builder', 'templates', 'ai-assistant'],
  },
  {
    slug: 'templates',
    icon: 'i-lucide-layout-grid',
    shot: shot('templates', 2320, 1180),
    cardIcons: ['i-lucide-folders', 'i-lucide-pencil-ruler', 'i-lucide-bookmark-plus', 'i-lucide-sparkles'],
    related: ['form-builder', 'design', 'ai-assistant'],
  },
  {
    slug: 'responses',
    demo: 'responses',
    icon: 'i-lucide-inbox',
    shot: shot('responses', 2320, 1180, true),
    cardIcons: [
      'i-lucide-table',
      'i-lucide-circle-check',
      'i-lucide-tags',
      'i-lucide-file-pen',
      'i-lucide-download',
      'i-lucide-sparkles',
    ],
    related: ['analytics', 'data-sources', 'api-service'],
  },
  {
    slug: 'analytics',
    demo: 'dashboard',
    icon: 'i-lucide-chart-column',
    shot: shot('analytics', 1528, 1036, true),
    cardIcons: [
      'i-lucide-funnel',
      'i-lucide-chart-no-axes-column-decreasing',
      'i-lucide-monitor-smartphone',
      'i-lucide-layout-dashboard',
      'i-lucide-calendar-range',
    ],
    related: ['responses', 'data-sources', 'form-builder'],
  },
  {
    slug: 'data-sources',
    demo: 'data',
    icon: 'i-lucide-database',
    shot: shot('data-sources', 2320, 1300, true),
    cardIcons: [
      'i-lucide-database',
      'i-lucide-arrow-down-to-line',
      'i-lucide-activity',
      'i-lucide-table-2',
      'i-lucide-square-terminal',
      'i-lucide-scroll-text',
    ],
    related: ['api-service', 'responses', 'access-control'],
  },
  {
    slug: 'api-service',
    demo: 'api',
    icon: 'i-lucide-braces',
    shot: shot('api-service', 2320, 1300, true),
    cardIcons: [
      'i-lucide-route',
      'i-lucide-key-round',
      'i-lucide-signature',
      'i-lucide-shield',
      'i-lucide-gauge',
      'i-lucide-book-open-text',
    ],
    related: ['data-sources', 'access-control', 'responses'],
  },
  {
    slug: 'access-control',
    icon: 'i-lucide-shield-check',
    shot: shot('roles-access', 2320, 1180),
    cardIcons: [
      'i-lucide-user-cog',
      'i-lucide-folder-lock',
      'i-lucide-eye',
      'i-lucide-building-2',
      'i-lucide-smartphone',
      'i-lucide-scroll-text',
    ],
    related: ['data-sources', 'api-service', 'responses'],
  },
  {
    slug: 'ai-assistant',
    icon: 'i-lucide-sparkles',
    visual: 'ai',
    cardIcons: [
      'i-lucide-wand-sparkles',
      'i-lucide-message-square-text',
      'i-lucide-chart-spline',
      'i-lucide-languages',
      'i-lucide-palette',
      'i-lucide-coins',
    ],
    related: ['form-builder', 'responses', 'languages'],
  },
  {
    slug: 'languages',
    icon: 'i-lucide-languages',
    visual: 'languages',
    cardIcons: ['i-lucide-globe', 'i-lucide-languages', 'i-lucide-sparkles', 'i-lucide-calendar-clock'],
    related: ['form-builder', 'ai-assistant', 'help-and-tours'],
  },
  {
    slug: 'help-and-tours',
    icon: 'i-lucide-life-buoy',
    shot: shot('help-centre', 2318, 1180),
    cardIcons: [
      'i-lucide-book-open',
      'i-lucide-bot',
      'i-lucide-circle-help',
      'i-lucide-map',
      'i-lucide-wand',
    ],
    related: ['languages', 'ai-assistant', 'form-builder'],
  },
]

export interface SolutionPage {
  slug: string
  /** The key of its menu entry (`solutions.{navKey}`). */
  navKey: string
  icon: string
  templateIcons: [string, string]
  /** Where the answers end up, drawn as a small flow. */
  destinations: string[]
  features: string[]
}

export const SOLUTION_PAGES: SolutionPage[] = [
  {
    slug: 'hr',
    navKey: 'hr',
    icon: 'i-lucide-users',
    templateIcons: ['i-lucide-briefcase', 'i-lucide-user-plus'],
    destinations: ['i-lucide-database', 'i-lucide-shield-check', 'i-lucide-mail-check'],
    features: ['access-control', 'data-sources', 'form-builder'],
  },
  {
    slug: 'customer-feedback',
    navKey: 'customerFeedback',
    icon: 'i-lucide-message-square-heart',
    templateIcons: ['i-lucide-star', 'i-lucide-package-open'],
    destinations: ['i-lucide-tags', 'i-lucide-chart-column', 'i-lucide-webhook'],
    features: ['analytics', 'languages', 'responses'],
  },
  {
    slug: 'events',
    navKey: 'events',
    icon: 'i-lucide-calendar-check',
    templateIcons: ['i-lucide-ticket', 'i-lucide-mail-question'],
    destinations: ['i-lucide-list-checks', 'i-lucide-mail-check', 'i-lucide-database'],
    features: ['form-builder', 'responses', 'design'],
  },
  {
    slug: 'health-and-safety',
    navKey: 'healthSafety',
    icon: 'i-lucide-hard-hat',
    templateIcons: ['i-lucide-triangle-alert', 'i-lucide-clipboard-list'],
    destinations: ['i-lucide-bell-ring', 'i-lucide-scroll-text', 'i-lucide-database'],
    features: ['form-builder', 'access-control', 'responses'],
  },
  {
    slug: 'education',
    navKey: 'education',
    icon: 'i-lucide-graduation-cap',
    templateIcons: ['i-lucide-school', 'i-lucide-clipboard-pen'],
    destinations: ['i-lucide-database', 'i-lucide-chart-column', 'i-lucide-languages'],
    features: ['languages', 'form-builder', 'analytics'],
  },
  {
    slug: 'operations',
    navKey: 'operations',
    icon: 'i-lucide-clipboard-check',
    templateIcons: ['i-lucide-truck', 'i-lucide-list-checks'],
    destinations: ['i-lucide-circle-check', 'i-lucide-database', 'i-lucide-scroll-text'],
    features: ['form-builder', 'data-sources', 'responses'],
  },
  {
    slug: 'developers',
    navKey: 'developers',
    icon: 'i-lucide-terminal',
    templateIcons: ['i-lucide-user-plus', 'i-lucide-webhook'],
    destinations: ['i-lucide-shield-check', 'i-lucide-database', 'i-lucide-webhook'],
    features: ['api-service', 'data-sources', 'access-control'],
  },
]

export const featurePage = (slug: string) => FEATURE_PAGES.find(page => page.slug === slug)
export const solutionPage = (slug: string) => SOLUTION_PAGES.find(page => page.slug === slug)

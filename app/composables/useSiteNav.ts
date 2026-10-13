import type { NavigationMenuItem } from '@nuxt/ui'

/**
 * The site's navigation, shared by the header, the phone menu and the footer (docs/SITEMAP.md).
 * Labels come from i18n and every address is localised, so the lists follow the page's language.
 */
export function useSiteNav() {
  const { t } = useI18n()
  const localePath = useLocalePath()
  const links = useSiteLinks()

  const item = (group: string, key: string, icon: string, to: string): NavigationMenuItem => ({
    label: t(`${group}.${key}.label`),
    description: t(`${group}.${key}.description`),
    icon,
    to,
  })

  const product = computed<NavigationMenuItem[]>(() => [
    item('product', 'formBuilder', 'i-lucide-layout-template', localePath('/features/form-builder')),
    item('product', 'design', 'i-lucide-palette', localePath('/features/design')),
    item('product', 'responses', 'i-lucide-chart-column', localePath('/features/responses')),
    item('product', 'dataSources', 'i-lucide-database', localePath('/features/data-sources')),
    item('product', 'apiService', 'i-lucide-braces', localePath('/features/api-service')),
    item('product', 'access', 'i-lucide-shield-check', localePath('/features/access-control')),
    item('product', 'ai', 'i-lucide-sparkles', localePath('/features/ai-assistant')),
    item('product', 'languages', 'i-lucide-languages', localePath('/features/languages')),
  ])

  const solutions = computed<NavigationMenuItem[]>(() => [
    item('solutions', 'hr', 'i-lucide-users', localePath('/solutions/hr')),
    item(
      'solutions',
      'customerFeedback',
      'i-lucide-message-square-heart',
      localePath('/solutions/customer-feedback'),
    ),
    item('solutions', 'events', 'i-lucide-calendar-check', localePath('/solutions/events')),
    item('solutions', 'healthSafety', 'i-lucide-hard-hat', localePath('/solutions/health-and-safety')),
    item('solutions', 'education', 'i-lucide-graduation-cap', localePath('/solutions/education')),
    item('solutions', 'operations', 'i-lucide-clipboard-check', localePath('/solutions/operations')),
    item('solutions', 'developers', 'i-lucide-terminal', localePath('/solutions/developers')),
  ])

  const resources = computed<NavigationMenuItem[]>(() => [
    // The help centre lives in the portal (people sign in to read it).
    { ...item('resources', 'helpCentre', 'i-lucide-life-buoy', `${links.portal}/help`), target: '_blank' },
    item('resources', 'blog', 'i-lucide-newspaper', localePath('/blog')),
    item('resources', 'changelog', 'i-lucide-history', localePath('/changelog')),
    item('resources', 'apiDocs', 'i-lucide-book-open-text', localePath('/features/api-service')),
  ])

  const company = computed<NavigationMenuItem[]>(() => [
    { label: t('company.about'), to: localePath('/about') },
    { label: t('company.security'), to: localePath('/security') },
    { label: t('company.trust'), to: localePath('/trust') },
    { label: t('company.enterprise'), to: localePath('/enterprise') },
    { label: t('nav.contact'), to: localePath('/contact') },
  ])

  // The legal documents in the order of the legal navigation (docs/LEGAL-PAGES.md).
  const legal = computed<NavigationMenuItem[]>(() =>
    (
      [
        ['privacy', 'privacy'],
        ['terms', 'terms'],
        ['dataProtection', 'data-protection'],
        ['cookies', 'cookies'],
        ['acceptableUse', 'acceptable-use'],
        ['subprocessors', 'subprocessors'],
        ['refunds', 'refunds'],
      ] as const
    ).map(([key, slug]) => ({ label: t(`legal.${key}`), to: localePath(`/legal/${slug}`) })),
  )

  const main = computed<NavigationMenuItem[]>(() => [
    { label: t('nav.product'), slot: 'panel' as const, children: product.value },
    { label: t('nav.solutions'), slot: 'panel' as const, children: solutions.value },
    { label: t('nav.pricing'), to: localePath('/pricing') },
    { label: t('nav.integrations'), to: localePath('/integrations') },
    { label: t('nav.resources'), slot: 'panel' as const, children: resources.value },
    { label: t('nav.contact'), to: localePath('/contact') },
  ])

  return { main, product, solutions, resources, company, legal }
}

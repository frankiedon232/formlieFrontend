<script setup lang="ts">
// The home page (docs/SITEMAP.md, docs/CONTENT.md), with the site's main structured data (docs/SEO.md):
// Organization, WebSite and SoftwareApplication with one Offer per plan and period from GET /public/plans.
const { t, locale } = useI18n()
const links = useSiteLinks()
const localePath = useLocalePath()
const { plans } = usePlans()

const offers = computed(() =>
  plans.value.flatMap(plan =>
    plan.prices
      ? (['monthly', 'quarterly', 'annually'] as const).map(period => ({
          '@type': 'Offer',
          name: `${t(`home.pricing.plans.${plan.id}`)} (${period})`,
          price: plan.prices![period],
          priceCurrency: plan.currency,
          url: `${links.site}${localePath('/pricing')}`,
        }))
      : [],
  ),
)

usePageSeo({
  title: () => t('home.meta.title'),
  fullTitle: () => t('home.meta.title'),
  description: () => t('site.description'),
  schema: () => [
    {
      '@context': 'https://schema.org',
      '@type': 'Organization',
      '@id': `${links.site}/#organization`,
      name: 'Formalie',
      url: links.site,
      logo: `${links.site}/icon-512.png`,
      slogan: t('site.tagline'),
      contactPoint: [
        { '@type': 'ContactPoint', contactType: 'customer support', email: 'support@formalie.com' },
        { '@type': 'ContactPoint', contactType: 'sales', email: 'sales@formalie.com' },
      ],
    },
    {
      '@context': 'https://schema.org',
      '@type': 'WebSite',
      '@id': `${links.site}/#website`,
      name: 'Formalie',
      url: links.site,
      inLanguage: SITE_LOCALES.map(item => item.language),
      publisher: { '@id': `${links.site}/#organization` },
    },
    {
      '@context': 'https://schema.org',
      '@type': 'SoftwareApplication',
      name: 'Formalie',
      description: t('site.description'),
      applicationCategory: 'BusinessApplication',
      operatingSystem: 'Web',
      inLanguage: locale.value,
      url: links.site,
      offers: offers.value,
      publisher: { '@id': `${links.site}/#organization` },
    },
  ],
})
</script>

<template>
  <div>
    <HomeHero />
    <HomeTrust />
    <HomeChannels />
    <HomeProductTabs />
    <HomeApart />
    <HomeSecurity />
    <HomeIntegrations />
    <HomeLanguages />
    <HomePricingTeaser />
    <HomeFaq />
    <SiteCta />
  </div>
</template>

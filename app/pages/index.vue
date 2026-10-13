<script setup lang="ts">
// The home page (docs/SITEMAP.md, docs/CONTENT.md).
const { t } = useI18n()
const links = useSiteLinks()

useSeoMeta({
  title: () => t('home.meta.title'),
  description: () => t('site.description'),
  ogTitle: () => t('home.meta.title'),
  ogDescription: () => t('site.description'),
  ogImage: `${links.site}/og-image.png`,
  twitterCard: 'summary_large_image',
})

useHead({
  script: [
    {
      key: 'org-schema',
      type: 'application/ld+json',
      innerHTML: JSON.stringify({
        '@context': 'https://schema.org',
        '@type': 'Organization',
        name: 'Formalie',
        url: links.site,
        logo: `${links.site}/icon-512.png`,
      }),
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
    <HomeCta />
  </div>
</template>

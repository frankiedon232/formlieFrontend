<script setup lang="ts">
// One blog article from content/blog (docs/SITEMAP.md), with Article structured data (docs/SEO.md).
const route = useRoute()
const { t, locale } = useI18n()
const links = useSiteLinks()

const { data: article } = await useAsyncData(`blog-${route.params.slug}`, () =>
  queryCollection('blog').path(`/blog/${route.params.slug}`).first(),
)
if (!article.value) throw createError({ statusCode: 404, statusMessage: 'Page not found', fatal: true })

usePageSeo({
  title: () => article.value?.title ?? '',
  description: () => article.value?.description ?? '',
  type: 'article',
  breadcrumbs: () => [
    { name: t('blogPage.title'), path: '/blog' },
    { name: article.value?.title ?? '', path: `/blog/${route.params.slug}` },
  ],
  schema: () => [
    {
      '@context': 'https://schema.org',
      '@type': 'Article',
      headline: article.value?.title,
      description: article.value?.description,
      datePublished: article.value?.date,
      inLanguage: 'en',
      publisher: { '@type': 'Organization', name: 'Formalie', logo: `${links.site}/icon-512.png` },
    },
  ],
})
</script>

<template>
  <UContainer v-if="article" class="max-w-3xl py-12 sm:py-16">
    <UPageHeader :title="article.title" :description="article.description">
      <template #headline>
        {{ new Intl.DateTimeFormat(locale, { dateStyle: 'long' }).format(new Date(article.date)) }}
      </template>
    </UPageHeader>
    <UPageBody>
      <ContentRenderer :value="article" />
    </UPageBody>
  </UContainer>
</template>

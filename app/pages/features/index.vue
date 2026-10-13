<script setup lang="ts">
// All features (docs/SITEMAP.md): one block per area with its screen, sides alternating, then the call to action.
const { t, tm, rt } = useI18n()
const localePath = useLocalePath()
const links = useSiteLinks()
const pages = FEATURE_PAGES

const bullets = (slug: string) =>
  (tm(`features.${slug}.cards`) as { title: unknown }[]).slice(0, 4).map(card => ({
    title: rt(card.title as string),
    icon: 'i-lucide-check',
  }))

usePageSeo({
  title: () => t('featuresIndex.title'),
  description: () => t('featuresIndex.metaDescription'),
  breadcrumbs: () => [{ name: t('nav.product'), path: '/features' }],
  schema: () => [
    {
      '@context': 'https://schema.org',
      '@type': 'ItemList',
      itemListElement: pages.map((page, i) => ({
        '@type': 'ListItem',
        position: i + 1,
        name: t(`features.${page.slug}.label`),
        url: `${links.site}${localePath(`/features/${page.slug}`)}`,
      })),
    },
  ],
})
</script>

<template>
  <div>
    <div class="relative isolate overflow-hidden">
      <div aria-hidden="true" class="absolute inset-x-0 -top-40 -z-10 flex justify-center">
        <div class="h-[26rem] w-[50rem] rounded-full bg-violet-500/10 blur-3xl dark:bg-violet-500/15" />
      </div>
      <UPageHero
        :title="t('featuresIndex.title')"
        :description="t('featuresIndex.description')"
        :links="[
          {
            label: t('nav.startFree'),
            to: links.signup('starter'),
            size: 'xl',
            color: 'neutral',
            trailingIcon: 'i-lucide-arrow-right',
          },
        ]"
        :ui="{ title: 'text-4xl sm:text-6xl font-semibold tracking-tight' }"
      >
        <template #headline>
          <UBadge
            :label="t('nav.product')"
            icon="i-lucide-sparkles"
            color="neutral"
            variant="outline"
            size="lg"
            class="rounded-full px-3"
          />
        </template>
        <!-- Every area as a chip, jumping to its block -->
        <ul class="mx-auto flex max-w-4xl flex-wrap justify-center gap-2">
          <li v-for="page in pages" :key="page.slug">
            <UButton
              :to="`#${page.slug}`"
              :label="t(`features.${page.slug}.label`)"
              :icon="page.icon"
              color="neutral"
              variant="subtle"
              class="rounded-full"
            />
          </li>
        </ul>
      </UPageHero>
    </div>

    <UPageSection
      v-for="(page, i) in pages"
      :id="page.slug"
      :key="page.slug"
      :headline="t(`features.${page.slug}.label`)"
      :title="t(`features.${page.slug}.title`)"
      :description="t(`features.${page.slug}.description`)"
      :features="bullets(page.slug)"
      :links="[
        {
          label: t('common.learnMore'),
          to: localePath(`/features/${page.slug}`),
          color: 'neutral',
          variant: 'outline',
          trailingIcon: 'i-lucide-arrow-right',
        },
      ]"
      orientation="horizontal"
      :reverse="i % 2 === 1"
      :ui="{
        container: 'py-14 sm:py-20 lg:py-24',
        title: 'text-2xl sm:text-3xl lg:text-4xl',
      }"
      class="scroll-mt-20"
    >
      <SiteScreenFrame v-if="page.shot" :shot="page.shot" :alt="t(`features.${page.slug}.alt`)" />
      <FeaturesVisualAi v-else-if="page.visual === 'ai'" />
      <FeaturesVisualLanguages v-else-if="page.visual === 'languages'" />
    </UPageSection>

    <SiteCta />
  </div>
</template>

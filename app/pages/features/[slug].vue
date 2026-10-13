<script setup lang="ts">
// One feature area (docs/SITEMAP.md): hero with the real screen (or a drawn visual), feature cards, how it works,
// related features and the call to action. Copy in i18n `features.{slug}`.
const route = useRoute()
const { t, tm, rt } = useI18n()
const localePath = useLocalePath()
const links = useSiteLinks()

const page = featurePage(String(route.params.slug))
if (!page) throw createError({ statusCode: 404, statusMessage: 'Page not found', fatal: true })

const base = `features.${page.slug}`
const cards = computed(() =>
  (tm(`${base}.cards`) as { title: unknown; text: unknown }[]).map((card, i) => ({
    title: rt(card.title as string),
    text: rt(card.text as string),
    icon: page.cardIcons[i] ?? page.icon,
  })),
)
const steps = computed(() =>
  (tm(`${base}.steps`) as { title: unknown; text: unknown }[]).map(step => ({
    title: rt(step.title as string),
    text: rt(step.text as string),
  })),
)

const actions = computed(() => [
  {
    label: t('nav.startFree'),
    to: links.signup('starter'),
    size: 'xl' as const,
    color: 'neutral' as const,
    trailingIcon: 'i-lucide-arrow-right',
  },
  {
    label: t('common.allFeatures'),
    to: localePath('/features'),
    size: 'xl' as const,
    color: 'neutral' as const,
    variant: 'outline' as const,
  },
])

usePageSeo({
  title: () => t(`${base}.label`),
  description: () => t(`${base}.metaDescription`),
  imageAlt: () => t(`${base}.title`),
  breadcrumbs: () => [
    { name: t('nav.product'), path: '/features' },
    { name: t(`${base}.label`), path: `/features/${page.slug}` },
  ],
  schema: () => [
    {
      '@context': 'https://schema.org',
      '@type': 'SoftwareApplication',
      name: `Formalie: ${t(`${base}.label`)}`,
      description: t(`${base}.metaDescription`),
      applicationCategory: 'BusinessApplication',
      operatingSystem: 'Web',
      url: `${links.site}${localePath(`/features/${page.slug}`)}`,
      featureList: cards.value.map(card => card.title),
      offers: { '@type': 'Offer', price: 0, priceCurrency: 'USD' },
    },
  ],
})
</script>

<template>
  <div v-if="page">
    <div class="relative isolate overflow-hidden">
      <div aria-hidden="true" class="absolute inset-x-0 -top-40 -z-10 flex justify-center">
        <div class="h-[26rem] w-[50rem] rounded-full bg-violet-500/10 blur-3xl dark:bg-violet-500/15" />
      </div>
      <UPageHero
        orientation="horizontal"
        :title="t(`${base}.title`)"
        :description="t(`${base}.description`)"
        :links="actions"
        :ui="{
          container: 'lg:grid-cols-[1fr_1.2fr] gap-12',
          description: 'text-base sm:text-lg',
        }"
      >
        <template #headline>
          <UBadge
            :label="t(`${base}.label`)"
            :icon="page.icon"
            color="neutral"
            variant="outline"
            size="lg"
            class="rounded-full px-3"
          />
        </template>

        <SiteScreenFrame
          v-if="page.shot"
          :shot="page.shot"
          :alt="t(`${base}.alt`)"
          eager
          tilt
          class="motion-safe:animate-rise"
        />
        <FeaturesVisualAi v-else-if="page.visual === 'ai'" class="motion-safe:animate-rise" />
        <FeaturesVisualLanguages v-else-if="page.visual === 'languages'" class="motion-safe:animate-rise" />
      </UPageHero>
    </div>

    <UPageSection>
      <UPageGrid>
        <UPageCard
          v-for="card in cards"
          :key="card.title"
          :title="card.title"
          :description="card.text"
          variant="subtle"
          spotlight
          spotlight-color="neutral"
          class="group"
        >
          <template #leading>
            <span
              class="flex size-11 items-center justify-center rounded-xl bg-inverted text-inverted shadow-lg shadow-black/10 transition-transform motion-safe:group-hover:-translate-y-0.5 motion-safe:group-hover:rotate-3"
            >
              <UIcon :name="card.icon" class="size-5" />
            </span>
          </template>
        </UPageCard>
      </UPageGrid>
    </UPageSection>

    <FeaturesSteps :steps="steps" />
    <FeaturesRelated :slugs="page.related" />
    <SiteCta />
  </div>
</template>

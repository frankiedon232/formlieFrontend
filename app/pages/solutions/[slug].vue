<script setup lang="ts">
// A solution (docs/SITEMAP.md, docs/CONTENT.md): the problem, the templates to start from, where the data goes,
// the features it uses and the call to action. Copy in i18n `solutionPages.{slug}`.
const route = useRoute()
const { t, tm, rt } = useI18n()
const localePath = useLocalePath()
const links = useSiteLinks()

const page = solutionPage(String(route.params.slug))
if (!page) throw createError({ statusCode: 404, statusMessage: 'Page not found', fatal: true })

const base = `solutionPages.${page.slug}`
const templates = computed(() =>
  (tm(`${base}.templates`) as { title: unknown; text: unknown }[]).map((item, i) => ({
    title: rt(item.title as string),
    text: rt(item.text as string),
    icon: page.templateIcons[i] ?? page.icon,
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
    label: t('home.hero.talkToSales'),
    to: `${localePath('/enterprise')}#enquiry`,
    size: 'xl' as const,
    color: 'neutral' as const,
    variant: 'outline' as const,
  },
])

usePageSeo({
  title: () => t(`solutions.${page.navKey}.label`),
  description: () => t(`${base}.metaDescription`),
  imageAlt: () => t(`${base}.title`),
  breadcrumbs: () => [{ name: t(`solutions.${page.navKey}.label`), path: `/solutions/${page.slug}` }],
  schema: () => [
    {
      '@context': 'https://schema.org',
      '@type': 'WebPage',
      name: t(`${base}.title`),
      description: t(`${base}.metaDescription`),
      about: templates.value.map(item => ({ '@type': 'Thing', name: item.title })),
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
          container: 'lg:grid-cols-[1fr_1.1fr] gap-12',
          description: 'text-base sm:text-lg',
        }"
      >
        <template #headline>
          <UBadge
            :label="t(`solutions.${page.navKey}.label`)"
            :icon="page.icon"
            color="neutral"
            variant="outline"
            size="lg"
            class="rounded-full px-3"
          />
        </template>
        <SolutionsFlow
          :templates="templates"
          :destinations="page.destinations"
          class="motion-safe:animate-rise"
        />
      </UPageHero>
    </div>

    <!-- The problem, then the forms to start from -->
    <UPageSection>
      <div class="grid gap-6 lg:grid-cols-3">
        <div class="rounded-2xl bg-elevated/60 p-6 ring-1 ring-default sm:p-8">
          <span
            class="flex size-10 items-center justify-center rounded-lg bg-amber-500/15 text-amber-600 dark:text-amber-400"
          >
            <UIcon name="i-lucide-triangle-alert" class="size-5" />
          </span>
          <h2 class="mt-5 text-sm font-semibold text-muted">{{ t('solutionPages.problem') }}</h2>
          <p class="mt-2 text-lg font-medium text-pretty text-highlighted">{{ t(`${base}.problem`) }}</p>
        </div>

        <div class="lg:col-span-2">
          <h2 class="text-2xl font-semibold tracking-tight text-highlighted sm:text-3xl">
            {{ t('common.startFrom') }}
          </h2>
          <div class="mt-6 grid gap-4 sm:grid-cols-2">
            <UPageCard
              v-for="item in templates"
              :key="item.title"
              :title="item.title"
              :description="item.text"
              :to="links.signup('starter')"
              variant="outline"
              class="group"
            >
              <template #leading>
                <span
                  class="flex size-11 items-center justify-center rounded-xl bg-inverted text-inverted shadow-lg shadow-black/10 transition-transform motion-safe:group-hover:-translate-y-0.5"
                >
                  <UIcon :name="item.icon" class="size-5" />
                </span>
              </template>
              <template #footer>
                <span class="flex items-center gap-1 text-sm font-medium text-highlighted">
                  {{ t('common.useTemplate') }}
                  <UIcon
                    name="i-lucide-arrow-right"
                    class="size-4 transition-transform group-hover:translate-x-0.5 rtl:group-hover:-translate-x-0.5"
                  />
                </span>
              </template>
            </UPageCard>
          </div>

          <div class="mt-6 flex items-start gap-4 rounded-2xl bg-inverted p-6 text-inverted">
            <UIcon name="i-lucide-route" class="mt-0.5 size-5 shrink-0" />
            <div>
              <h2 class="text-sm font-semibold opacity-70">{{ t('common.whereDataGoes') }}</h2>
              <p class="mt-1 text-base font-medium">{{ t(`${base}.data`) }}</p>
            </div>
          </div>
        </div>
      </div>
    </UPageSection>

    <FeaturesRelated :slugs="page.features" />
    <SiteCta />
  </div>
</template>

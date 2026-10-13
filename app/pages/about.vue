<script setup lang="ts">
// About (docs/SITEMAP.md): mission, what Formalie believes in, global by design. No invented numbers or people.
const { t, tm, rt } = useI18n()
const links = useSiteLinks()
const locales = SITE_LOCALES

const ICONS = ['i-lucide-eye-off', 'i-lucide-database', 'i-lucide-feather']
const beliefs = computed(() =>
  (tm('aboutPage.beliefs') as { title: unknown; text: unknown }[]).map((item, i) => ({
    title: rt(item.title as string),
    text: rt(item.text as string),
    icon: ICONS[i]!,
  })),
)

usePageSeo({
  title: () => t('company.about'),
  description: () => t('aboutPage.metaDescription'),
  breadcrumbs: () => [{ name: t('company.about'), path: '/about' }],
  schema: () => [
    {
      '@context': 'https://schema.org',
      '@type': 'AboutPage',
      name: t('aboutPage.title'),
      description: t('aboutPage.metaDescription'),
      mainEntity: { '@type': 'Organization', name: 'Formalie', url: links.site },
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
        :title="t('aboutPage.title')"
        :description="t('aboutPage.description')"
        :ui="{ title: 'text-balance' }"
      >
        <template #headline>
          <img
            src="/brand/formalie-mark-accent.svg"
            alt=""
            width="56"
            height="56"
            class="mx-auto size-14 rounded-2xl motion-safe:animate-float"
          />
        </template>
      </UPageHero>
    </div>

    <UPageSection :ui="{ container: 'py-6 sm:py-8 lg:py-10 lg:max-w-4xl' }">
      <div class="rounded-3xl bg-inverted p-8 text-center text-inverted sm:p-12">
        <h2 class="text-sm font-semibold opacity-70">{{ t('aboutPage.mission.title') }}</h2>
        <p class="mt-4 text-2xl font-semibold tracking-tight text-pretty sm:text-3xl">
          {{ t('aboutPage.mission.text') }}
        </p>
      </div>
    </UPageSection>

    <UPageSection :title="t('aboutPage.beliefsTitle')">
      <UPageGrid>
        <UPageCard
          v-for="item in beliefs"
          :key="item.title"
          :title="item.title"
          :description="item.text"
          variant="subtle"
        >
          <template #leading>
            <span
              class="flex size-11 items-center justify-center rounded-xl bg-inverted text-inverted shadow-lg shadow-black/10"
            >
              <UIcon :name="item.icon" class="size-5" />
            </span>
          </template>
        </UPageCard>
      </UPageGrid>
    </UPageSection>

    <UPageSection :title="t('aboutPage.global.title')" :description="t('aboutPage.global.text')">
      <ul class="mx-auto flex max-w-4xl flex-wrap justify-center gap-2">
        <li
          v-for="(item, i) in locales"
          :key="item.code"
          :lang="item.language"
          class="flex items-center gap-2 rounded-full bg-default px-3 py-1.5 text-sm font-medium text-highlighted ring-1 ring-default motion-safe:animate-rise"
          :style="{ animationDelay: `${i * 40}ms` }"
        >
          <UIcon :name="item.flag" class="size-4" />
          {{ item.name }}
        </li>
      </ul>
    </UPageSection>

    <LazySiteCta hydrate-on-visible />
  </div>
</template>

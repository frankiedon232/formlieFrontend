<script setup lang="ts">
// The blog and the changelog (docs/SITEMAP.md), from @nuxt/content (content/blog, content/changelog), newest first.
// Until the first entry exists the page says so plainly and asks search engines not to list it.
const props = defineProps<{ collection: 'blog' | 'changelog'; base: string }>()
const { t, locale } = useI18n()
const localePath = useLocalePath()

const { data: entries } = await useAsyncData(`list-${props.collection}`, () =>
  queryCollection(props.collection).order('date', 'DESC').all(),
)

const date = (value: string) =>
  new Intl.DateTimeFormat(locale.value, { dateStyle: 'long' }).format(new Date(value))
const page = `${props.collection}Page`

usePageSeo({
  title: () => t(`${page}.title`),
  description: () => t(`${page}.description`),
  breadcrumbs: () => [{ name: t(`${page}.title`), path: props.base }],
  noindex: !entries.value?.length,
})
</script>

<template>
  <div>
    <div class="relative isolate overflow-hidden">
      <div aria-hidden="true" class="absolute inset-x-0 -top-40 -z-10 flex justify-center">
        <div class="h-[26rem] w-[50rem] rounded-full bg-violet-500/10 blur-3xl dark:bg-violet-500/15" />
      </div>
      <UPageHero
        :title="t(`${page}.title`)"
        :description="t(`${page}.description`)"
        :ui="{ container: 'pb-6 sm:pb-8 lg:pb-10' }"
      />
    </div>

    <UContainer class="pb-16 sm:pb-20">
      <UBlogPosts v-if="entries?.length" class="lg:grid-cols-2">
        <UBlogPost
          v-for="entry in entries"
          :key="entry.path"
          :title="entry.title"
          :description="entry.description"
          :date="date(entry.date)"
          :to="localePath(entry.path)"
          variant="outline"
        />
      </UBlogPosts>

      <!-- Nothing published yet -->
      <div v-else class="mx-auto max-w-xl rounded-3xl bg-elevated/40 p-10 text-center ring-1 ring-default">
        <span
          class="mx-auto flex size-12 items-center justify-center rounded-2xl bg-inverted text-inverted shadow-lg shadow-black/10"
        >
          <UIcon :name="collection === 'blog' ? 'i-lucide-newspaper' : 'i-lucide-history'" class="size-5" />
        </span>
        <h2 class="mt-5 text-xl font-semibold tracking-tight text-highlighted">{{ t(`${page}.empty`) }}</h2>
        <p class="mt-2 text-muted">{{ t('blogPage.emptyText') }}</p>
        <UButton
          :to="localePath('/features')"
          :label="t('common.allFeatures')"
          color="neutral"
          class="mt-6"
          trailing-icon="i-lucide-arrow-right"
        />
      </div>
    </UContainer>
  </div>
</template>

<!--
  A help article (F25 M1): title and summary in the header, the article in a readable column, "On this page"
  and related articles beside it, "Was this helpful?" under it. Says when it is shown in English because it
  isn't translated yet.
-->
<script setup lang="ts">
import type { HelpArticle, HelpCategory } from '#shared/types/help'
import { HELP_CATEGORY_ICONS } from '#shared/utils/help/categories'

definePageMeta({ breadcrumb: 'nav.help' })
const { t, d, locale } = useI18n()
const api = useApi()
const route = useRoute()
const { handle } = useErrorHandler()
const { setLabel } = useBreadcrumbs()

const id = computed(() => String(route.params.article))
const category = computed(() => String(route.params.category) as HelpCategory)
const article = ref<HelpArticle | null>(null)
const failed = ref(false)
const missing = ref(false)
async function load() {
  failed.value = false
  missing.value = false
  try {
    article.value = (await api.get<HelpArticle>(`/help/articles/${id.value}`, { lang: locale.value })).data
  } catch (error) {
    if ((error as { code?: string }).code === 'FRM-GEN-1004') missing.value = true
    else failed.value = true
    handle(error, { silent: true })
  }
}
watch([id, locale], () => void load(), { immediate: true })
watchEffect(() => {
  setLabel(`/help/${category.value}`, t(`help.category.${category.value}.name`))
  if (article.value) setLabel(`/help/${category.value}/${id.value}`, article.value.title)
})
useHead({ title: () => article.value?.title ?? t('nav.help') })

const body = useTemplateRef<{ headings: { id: string; text: string }[] }>('body')
const headings = computed(() => body.value?.headings ?? [])
const day = (iso: string) => d(new Date(iso), { day: 'numeric', month: 'long', year: 'numeric' })
</script>

<template>
  <AppPanel id="help-article" :title="article?.title ?? t('nav.help')" :subtitle="article?.summary" :subtitle-icon="HELP_CATEGORY_ICONS[category] ?? 'i-lucide-circle-help'">
    <template #actions>
      <UButton :label="t(`help.category.${category}.name`)" icon="i-lucide-arrow-left" color="neutral" variant="outline" :to="`/help/${category}`" class="max-sm:hidden" />
      <UButton :label="t('help.back')" icon="i-lucide-circle-help" color="neutral" variant="outline" to="/help" />
    </template>

    <AppEmpty v-if="missing" icon="i-lucide-file-question" :title="t('help.notFound')" :description="t('help.notFoundDesc')" :actions="[{ label: t('help.back'), color: 'neutral', to: '/help' }]" />
    <AppEmpty v-else-if="failed && !article" icon="i-lucide-cloud-alert" :title="t('dataView.errorTitle')" :actions="[{ label: t('common.retry'), icon: 'i-lucide-refresh-cw', color: 'neutral', variant: 'outline', onClick: load }]" />
    <div v-else-if="!article" class="flex max-w-3xl flex-col gap-3"><USkeleton v-for="n in 6" :key="n" class="h-5 w-full" /></div>
    <div v-else class="grid items-start gap-6 lg:grid-cols-[minmax(0,1fr)_16rem]">
      <article class="flex max-w-3xl min-w-0 flex-col gap-6">
        <div class="flex flex-wrap items-center gap-2 text-xs text-muted">
          <UBadge :label="t(`help.category.${article.category}.name`)" :icon="HELP_CATEGORY_ICONS[article.category]" color="neutral" variant="outline" size="sm" class="rounded-md" />
          <span>{{ t('help.minutes', { n: article.minutes }, article.minutes) }}</span>
          <span>· {{ t('help.updated', { date: day(article.updated_at) }) }}</span>
        </div>
        <UAlert v-if="article.language !== locale" color="neutral" variant="subtle" icon="i-lucide-languages" :title="t('help.notTranslated')" />
        <HelpBlocks ref="body" :blocks="article.blocks" />
        <HelpFeedback :article-id="article.id" :initial="article.helpful" />
      </article>

      <aside class="flex flex-col gap-4 lg:sticky lg:top-0">
        <nav v-if="headings.length" class="flex flex-col gap-1 rounded-lg border border-default p-4" :aria-label="t('help.onThisPage')">
          <span class="text-xs font-medium text-muted uppercase">{{ t('help.onThisPage') }}</span>
          <a v-for="heading in headings" :key="heading.id" :href="`#${heading.id}`" class="rounded-sm text-sm text-default hover:text-highlighted focus-visible:outline-2 focus-visible:outline-(--ui-border-inverted)">{{ heading.text }}</a>
        </nav>
        <div v-if="article.related.length" class="flex flex-col gap-1 rounded-lg border border-default p-3">
          <span class="px-1 text-xs font-medium text-muted uppercase">{{ t('help.related') }}</span>
          <HelpArticleList :articles="article.related" compact />
        </div>
      </aside>
    </div>
  </AppPanel>
</template>

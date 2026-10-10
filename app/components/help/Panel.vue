<!--
  The help panel (F25 M3), opened by the "?" in every page header (H) or from an empty state: the article for
  the page you are on (or the one asked for), more help for the page, its guided tour, a search into the help
  centre. Esc closes; nothing on the page is lost.
-->
<script setup lang="ts">
import type { HelpArticle, HelpContext } from '#shared/types/help'
import { helpArticlePath } from '#shared/utils/help/categories'

const { t, locale } = useI18n()
const api = useApi()
const route = useRoute()
const { handle } = useErrorHandler()
const help = useHelpPanel()

const context = ref<HelpContext | null>(null)
const loading = ref(false)
const failed = ref(false)
async function load() {
  loading.value = true
  failed.value = false
  try {
    if (help.articleId.value) {
      const article = (await api.get<HelpArticle>(`/help/articles/${help.articleId.value}`, { lang: locale.value })).data
      context.value = { article, more: [], tour: null }
    } else context.value = (await api.get<HelpContext>('/help/context', { path: route.path, lang: locale.value })).data
  } catch (error) {
    failed.value = true
    handle(error, { silent: true })
  } finally {
    loading.value = false
  }
}
watch(
  () => [help.open.value, help.articleId.value, route.path, locale.value] as const,
  ([isOpen]) => isOpen && void load(),
)
const query = ref('')
function search() {
  if (!query.value.trim()) return
  help.open.value = false
  void navigateTo({ path: '/help', query: { q: query.value.trim() } })
}
const close = () => (help.open.value = false)
</script>

<template>
  <USlideover v-model:open="help.open.value" :title="t('help.panel.title')" :description="t('help.panel.desc')" :ui="{ content: 'w-full sm:max-w-md', body: 'flex flex-col gap-5' }">
    <template #body>
      <form class="flex gap-2" @submit.prevent="search">
        <UInput v-model="query" icon="i-lucide-search" :placeholder="t('help.search.placeholder')" class="min-w-0 flex-1" :aria-label="t('help.search.title')" />
        <UButton type="submit" icon="i-lucide-arrow-right" color="neutral" variant="outline" square :aria-label="t('help.search.title')" />
      </form>

      <div v-if="loading && !context" class="flex flex-col gap-3"><USkeleton class="h-6 w-2/3" /><USkeleton v-for="n in 4" :key="n" class="h-4 w-full" /></div>
      <AppEmpty v-else-if="failed && !context" size="sm" icon="i-lucide-cloud-alert" :title="t('dataView.errorTitle')" :actions="[{ label: t('common.retry'), color: 'neutral', variant: 'outline', onClick: load }]" />
      <template v-else-if="context">
        <UButton v-if="context.tour" :label="t('help.tour.start', { title: context.tour.title })" icon="i-lucide-route" color="neutral" class="justify-center" @click="help.startTour(context.tour!)" />

        <article v-if="context.article" class="flex flex-col gap-3 transition-opacity" :class="loading ? 'opacity-60' : ''">
          <h3 class="text-base font-semibold text-highlighted">{{ context.article.title }}</h3>
          <p class="text-sm text-muted">{{ context.article.summary }}</p>
          <HelpBlocks :blocks="context.article.blocks" compact @show="close" />
          <UButton :label="t('help.panel.openFull')" trailing-icon="i-lucide-arrow-up-right" color="neutral" variant="outline" size="sm" class="self-start" :to="helpArticlePath(context.article)" @click="close" />
          <HelpFeedback :article-id="context.article.id" :initial="context.article.helpful" />
        </article>
        <AppEmpty v-else size="sm" icon="i-lucide-book-open" :title="t('help.panel.none')" :description="t('help.panel.noneDesc')" />

        <div v-if="context.more.length || context.article?.related.length" class="flex flex-col gap-1">
          <span class="text-xs font-medium text-muted uppercase">{{ t('help.panel.more') }}</span>
          <HelpArticleList :articles="context.more.length ? context.more : context.article!.related" compact @click="close" />
        </div>
      </template>
    </template>
    <template #footer>
      <div class="flex w-full items-center justify-between gap-2">
        <UButton :label="t('help.panel.centre')" icon="i-lucide-circle-help" color="neutral" variant="ghost" to="/help" @click="close" />
        <UButton :label="t('common.close')" color="neutral" @click="close" />
      </div>
    </template>
  </USlideover>
</template>

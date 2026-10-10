<!--
  Help & support (F25 M1): search across articles, FAQs and the glossary (in the address, ?q=), the "New here?"
  path, every area of the knowledge base, popular articles, and how to reach a person. Content is published by
  the Formalie team in the platform admin, in the reader's language (English while a text isn't translated).
-->
<script setup lang="ts">
import type { HelpHome, HelpSearchResult } from '#shared/types/help'
import { HELP_CATEGORY_ICONS, helpArticlePath } from '#shared/utils/help/categories'

definePageMeta({ breadcrumb: 'nav.help' })
const { t, locale } = useI18n()
const { contact } = useSupport()
useHead({ title: () => t('nav.help') })
const api = useApi()
const route = useRoute()
const router = useRouter()
const { handle } = useErrorHandler()
const { can } = useCan()
// The assistant answers from the knowledge base when it is on and the person may use it (F25 M4)
const ai = useAi()
onMounted(() => can('ai.use') && void ai.load())

const home = ref<HelpHome | null>(null)
const failed = ref(false)
async function load() {
  failed.value = false
  try {
    home.value = (await api.get<HelpHome>('/help/home', { lang: locale.value })).data
  } catch (error) {
    failed.value = true
    handle(error, { silent: true })
  }
}
watch(locale, () => void load())
onMounted(load)

// Search lives in the address so it can be shared and survives going back
const query = ref(typeof route.query.q === 'string' ? route.query.q : '')
const result = ref<HelpSearchResult | null>(null)
const searching = ref(false)
const ids = ref<Record<string, string>>({})
async function search(q: string) {
  void router.replace({ query: { ...route.query, q: q.trim() || undefined } })
  if (!q.trim()) return void (result.value = null)
  searching.value = true
  try {
    result.value = (await api.get<HelpSearchResult>('/help/search', { q: q.trim(), lang: locale.value })).data
    for (const article of result.value.articles) ids.value[article.id] = article.category
  } catch (error) {
    handle(error)
  } finally {
    searching.value = false
  }
}
watchDebounced(query, value => void search(value), { debounce: 300 })
onMounted(async () => {
  if (query.value) void search(query.value)
  // FAQs and terms link to articles: know each article's area once
  try {
    const { data } = await api.get<{ id: string; category: string }[]>('/help/articles', { lang: locale.value }, { background: true })
    ids.value = Object.fromEntries(data.map(item => [item.id, item.category]))
  } catch {
    ids.value = {}
  }
})
const input = useTemplateRef<{ inputRef?: HTMLInputElement }>('input')
defineShortcuts({ '/': { handler: () => input.value?.inputRef?.focus() } })
</script>

<template>
  <AppPanel id="help" :title="t('nav.help')" :subtitle="t('help.subtitle')" subtitle-icon="i-lucide-circle-help">
    <template #actions>
      <UButton :label="t('help.faq.title')" icon="i-lucide-messages-square" color="neutral" variant="outline" to="/help/faq" class="max-sm:hidden" data-help="help-faq" />
      <UButton :label="t('help.support.contact')" icon="i-lucide-life-buoy" color="neutral" data-help="help-contact" @click="contact()" />
    </template>

    <UCard variant="outline" class="shrink-0" :ui="{ body: 'flex flex-col gap-3 p-4 sm:p-6' }">
      <h2 class="text-lg font-semibold text-highlighted">{{ t('help.search.title') }}</h2>
      <UInput ref="input" v-model="query" data-help="help-search" icon="i-lucide-search" size="xl" :placeholder="t('help.search.placeholder')" class="w-full" :aria-label="t('help.search.title')">
        <template #trailing><UKbd value="/" /></template>
      </UInput>
      <div class="flex flex-wrap gap-1.5">
        <UButton v-for="example in ['publish', 'logic', 'export', 'roles', 'translate']" :key="example" :label="t(`help.search.example.${example}`)" color="neutral" variant="outline" size="xs" class="rounded-full" @click="query = t(`help.search.example.${example}`)" />
      </div>
    </UCard>

    <HelpSearchResults v-if="query.trim()" :result="result" :loading="searching" :show-answer="can('ai.use') && ai.enabled.value" :support="true" :category-of="id => ids[id]" @clear="query = ''" />
    <AppEmpty v-else-if="failed && !home" icon="i-lucide-cloud-alert" :title="t('dataView.errorTitle')" :actions="[{ label: t('common.retry'), icon: 'i-lucide-refresh-cw', color: 'neutral', variant: 'outline', onClick: load }]" />
    <div v-else-if="!home" class="flex flex-col gap-4"><USkeleton class="h-32 w-full rounded-lg" /><div class="grid gap-3 sm:grid-cols-3"><USkeleton v-for="n in 6" :key="n" class="h-24 rounded-lg" /></div></div>
    <template v-else>
      <section class="flex flex-col gap-3">
        <h2 class="text-sm font-semibold text-highlighted">{{ t('help.start.title') }}</h2>
        <ol class="grid gap-3 sm:grid-cols-2 xl:grid-cols-5">
          <li v-for="(article, index) in home.start" :key="article.id">
            <NuxtLink :to="helpArticlePath(article)" class="flex h-full flex-col gap-2 rounded-lg border border-default p-4 transition-all hover:-translate-y-0.5 hover:border-accented hover:shadow-md focus-visible:outline-2 focus-visible:outline-(--ui-border-inverted)">
              <span class="flex size-7 items-center justify-center rounded-full bg-inverted text-xs font-semibold text-inverted tabular-nums">{{ index + 1 }}</span>
              <span class="text-sm font-semibold text-highlighted">{{ article.title }}</span>
              <span class="text-xs text-muted">{{ article.summary }}</span>
            </NuxtLink>
          </li>
        </ol>
      </section>

      <section class="flex flex-col gap-3">
        <h2 class="text-sm font-semibold text-highlighted">{{ t('help.areas') }}</h2>
        <div class="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
          <UPageCard
            v-for="category in home.categories.filter(item => item.key !== 'start')"
            :key="category.key"
            :to="`/help/${category.key}`"
            :icon="HELP_CATEGORY_ICONS[category.key]"
            :title="t(`help.category.${category.key}.name`)"
            :description="t(`help.category.${category.key}.desc`)"
            variant="outline"
            class="h-full transition-all hover:-translate-y-0.5 hover:shadow-md"
            :ui="{ leadingIcon: 'size-5 text-default' }"
          >
            <template #footer><span class="text-xs text-muted">{{ t('help.articles', { n: category.count }, category.count) }}</span></template>
          </UPageCard>
        </div>
      </section>

      <div class="grid gap-4 lg:grid-cols-[minmax(0,2fr)_minmax(0,1fr)]">
        <UCard variant="outline" :ui="{ body: 'p-3 sm:p-4' }">
          <h2 class="px-1 text-sm font-semibold text-highlighted">{{ t('help.popular') }}</h2>
          <HelpArticleList :articles="home.popular" show-area />
        </UCard>
        <div class="flex flex-col gap-4">
          <UCard variant="outline" :ui="{ body: 'flex flex-col gap-2 p-4 sm:p-5' }">
            <h2 class="text-sm font-semibold text-highlighted">{{ t('help.more.title') }}</h2>
            <UButton :label="t('help.faq.title')" icon="i-lucide-messages-square" color="neutral" variant="ghost" class="justify-start" to="/help/faq" />
            <UButton :label="t('help.glossary.title')" icon="i-lucide-book-a" color="neutral" variant="ghost" class="justify-start" to="/help/glossary" />
            <UButton :label="t('help.shortcuts.title')" icon="i-lucide-keyboard" color="neutral" variant="ghost" class="justify-start" to="/help/shortcuts" />
          </UCard>
          <UCard variant="outline" :ui="{ body: 'flex flex-col gap-2 p-4 sm:p-5' }">
            <h2 class="text-sm font-semibold text-highlighted">{{ t('help.support.title') }}</h2>
            <p class="text-sm text-muted">{{ t('help.support.desc') }}</p>
            <UButton :label="t('help.support.contact')" icon="i-lucide-life-buoy" color="neutral" class="self-start" @click="contact()" />
            <UButton v-if="home.support.url" :label="t('help.support.site')" icon="i-lucide-external-link" color="neutral" variant="outline" class="self-start" :to="home.support.url" target="_blank" />
          </UCard>
        </div>
      </div>
    </template>
  </AppPanel>
</template>

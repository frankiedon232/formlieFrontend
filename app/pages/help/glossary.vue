<!-- Help & support → Glossary (F25 M2): the words Formalie uses, A to Z in the reader's language, searchable, each with its article. -->
<script setup lang="ts">
import type { HelpCategory, HelpTerm } from '#shared/types/help'
import { helpArticlePath } from '#shared/utils/help/categories'

definePageMeta({ breadcrumb: 'help.glossary.title' })
const { t, locale } = useI18n()
useHead({ title: () => t('help.glossary.title') })
const api = useApi()
const { handle } = useErrorHandler()

const terms = ref<HelpTerm[] | null>(null)
const articles = ref<Record<string, HelpCategory>>({})
const failed = ref(false)
async function load() {
  failed.value = false
  try {
    const [list, index] = await Promise.all([api.get<HelpTerm[]>('/help/glossary', { lang: locale.value }), api.get<{ id: string; category: HelpCategory }[]>('/help/articles', { lang: locale.value })])
    terms.value = list.data
    articles.value = Object.fromEntries(index.data.map(item => [item.id, item.category]))
  } catch (error) {
    failed.value = true
    handle(error, { silent: true })
  }
}
watch(locale, () => void load(), { immediate: true })

const search = ref('')
const shown = computed(() => {
  const words = search.value.trim().toLocaleLowerCase()
  return (terms.value ?? []).filter(item => !words || `${item.term} ${item.definition}`.toLocaleLowerCase().includes(words))
})
/** Grouped by first letter (as the reader's language sorts them). */
const groups = computed(() => {
  const out = new Map<string, HelpTerm[]>()
  for (const term of shown.value) {
    const letter = term.term.charAt(0).toLocaleUpperCase(locale.value)
    out.set(letter, [...(out.get(letter) ?? []), term])
  }
  return [...out.entries()].map(([letter, items]) => ({ letter, items }))
})
const link = (term: HelpTerm) => (term.article && articles.value[term.article] ? helpArticlePath({ id: term.article, category: articles.value[term.article]! }) : null)
</script>

<template>
  <AppPanel id="help-glossary" :title="t('help.glossary.title')" :subtitle="t('help.glossary.desc')" subtitle-icon="i-lucide-book-a">
    <template #actions>
      <UButton :label="t('help.back')" icon="i-lucide-circle-help" color="neutral" variant="outline" to="/help" />
    </template>

    <AppEmpty v-if="failed && !terms" icon="i-lucide-cloud-alert" :title="t('dataView.errorTitle')" :actions="[{ label: t('common.retry'), icon: 'i-lucide-refresh-cw', color: 'neutral', variant: 'outline', onClick: load }]" />
    <div v-else-if="!terms" class="grid gap-2 sm:grid-cols-2"><USkeleton v-for="n in 8" :key="n" class="h-16 rounded-lg" /></div>
    <template v-else>
      <UInput v-model="search" icon="i-lucide-search" :placeholder="t('help.glossary.search')" class="w-full sm:max-w-md" :aria-label="t('help.glossary.search')" />
      <AppEmpty v-if="!groups.length" icon="i-lucide-search-x" :title="t('help.glossary.none')" :actions="[{ label: t('help.search.clear'), color: 'neutral', variant: 'outline', onClick: () => (search = '') }]" />
      <section v-for="group in groups" :key="group.letter" class="flex flex-col gap-2">
        <h2 class="text-sm font-semibold text-muted">{{ group.letter }}</h2>
        <dl class="grid gap-2 sm:grid-cols-2">
          <div v-for="term in group.items" :key="term.id" class="flex h-full flex-col gap-1 rounded-lg border border-default px-4 py-3">
            <dt class="text-sm font-semibold text-highlighted">{{ term.term }}</dt>
            <dd class="text-sm text-muted">{{ term.definition }}</dd>
            <dd v-if="link(term)" class="mt-auto"><UButton :label="t('help.readMore')" trailing-icon="i-lucide-arrow-right" color="neutral" variant="link" size="xs" class="px-0" :to="link(term)!" /></dd>
          </div>
        </dl>
      </section>
    </template>
  </AppPanel>
</template>

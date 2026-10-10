<!-- Help & support → Frequently asked questions (F25 M2): searchable, grouped by area (chips in a sliding row), each linking to its article. -->
<script setup lang="ts">
import { HELP_CATEGORIES, type HelpCategory, type HelpFaq } from '#shared/types/help'
import { HELP_CATEGORY_ICONS, helpArticlePath } from '#shared/utils/help/categories'

definePageMeta({ breadcrumb: 'help.faq.title' })
const { t, locale } = useI18n()
useHead({ title: () => t('help.faq.title') })
const api = useApi()
const { handle } = useErrorHandler()

const faqs = ref<HelpFaq[] | null>(null)
const articles = ref<Record<string, HelpCategory>>({})
const failed = ref(false)
async function load() {
  failed.value = false
  try {
    const [list, index] = await Promise.all([api.get<HelpFaq[]>('/help/faqs', { lang: locale.value }), api.get<{ id: string; category: HelpCategory }[]>('/help/articles', { lang: locale.value })])
    faqs.value = list.data
    articles.value = Object.fromEntries(index.data.map(item => [item.id, item.category]))
  } catch (error) {
    failed.value = true
    handle(error, { silent: true })
  }
}
watch(locale, () => void load(), { immediate: true })

const search = ref('')
const area = ref<HelpCategory | null>(null)
const shown = computed(() => {
  const words = search.value.trim().toLocaleLowerCase()
  return (faqs.value ?? []).filter(item => (!area.value || item.category === area.value) && (!words || `${item.question} ${item.answer}`.toLocaleLowerCase().includes(words)))
})
const groups = computed(() => HELP_CATEGORIES.map(key => ({ key, items: shown.value.filter(item => item.category === key) })).filter(group => group.items.length))
const areas = computed(() => HELP_CATEGORIES.filter(key => faqs.value?.some(item => item.category === key)))
const link = (faq: HelpFaq) => (faq.article && articles.value[faq.article] ? helpArticlePath({ id: faq.article, category: articles.value[faq.article]! }) : null)
</script>

<template>
  <AppPanel id="help-faq" :title="t('help.faq.title')" :subtitle="t('help.faq.desc')" subtitle-icon="i-lucide-messages-square">
    <template #actions>
      <UButton :label="t('help.back')" icon="i-lucide-circle-help" color="neutral" variant="outline" to="/help" />
    </template>

    <AppEmpty v-if="failed && !faqs" icon="i-lucide-cloud-alert" :title="t('dataView.errorTitle')" :actions="[{ label: t('common.retry'), icon: 'i-lucide-refresh-cw', color: 'neutral', variant: 'outline', onClick: load }]" />
    <div v-else-if="!faqs" class="flex flex-col gap-2"><USkeleton v-for="n in 6" :key="n" class="h-12 w-full rounded-lg" /></div>
    <template v-else>
      <div class="flex flex-col gap-3">
        <UInput v-model="search" icon="i-lucide-search" :placeholder="t('help.faq.search')" class="w-full sm:max-w-md" :aria-label="t('help.faq.search')" />
        <div class="-mx-1 flex gap-1.5 overflow-x-auto px-1 pb-1" role="group" :aria-label="t('help.areas')">
          <UButton :label="t('help.faq.all')" color="neutral" :variant="area ? 'outline' : 'solid'" size="xs" class="shrink-0 rounded-full" @click="area = null" />
          <UButton v-for="key in areas" :key="key" :label="t(`help.category.${key}.name`)" :icon="HELP_CATEGORY_ICONS[key]" color="neutral" :variant="area === key ? 'solid' : 'outline'" size="xs" class="shrink-0 rounded-full" :aria-pressed="area === key" @click="area = area === key ? null : key" />
        </div>
      </div>
      <AppEmpty v-if="!groups.length" icon="i-lucide-search-x" :title="t('help.faq.none')" :actions="[{ label: t('help.search.clear'), color: 'neutral', variant: 'outline', onClick: () => ((search = ''), (area = null)) }]" />
      <section v-for="group in groups" :key="group.key" class="flex flex-col gap-2">
        <h2 class="flex items-center gap-2 text-sm font-semibold text-highlighted"><UIcon :name="HELP_CATEGORY_ICONS[group.key]" class="size-4 text-muted" />{{ t(`help.category.${group.key}.name`) }}</h2>
        <details v-for="faq in group.items" :key="faq.id" class="rounded-lg border border-default px-4 py-3">
          <summary class="cursor-pointer list-none text-sm font-medium text-highlighted focus-visible:outline-2 focus-visible:outline-(--ui-border-inverted)">{{ faq.question }}</summary>
          <p class="mt-2 text-sm text-muted">{{ faq.answer }}</p>
          <UButton v-if="link(faq)" :label="t('help.readMore')" trailing-icon="i-lucide-arrow-right" color="neutral" variant="link" size="xs" class="mt-1 px-0" :to="link(faq)!" />
        </details>
      </section>
    </template>
  </AppPanel>
</template>

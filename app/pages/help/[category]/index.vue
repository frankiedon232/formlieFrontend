<!-- Help & support → an area of the knowledge base (F25 M1): its articles and its frequently asked questions. -->
<script setup lang="ts">
import { HELP_CATEGORIES, type HelpArticleSummary, type HelpCategory, type HelpFaq } from '#shared/types/help'
import { HELP_CATEGORY_ICONS, helpArticlePath } from '#shared/utils/help/categories'

definePageMeta({ breadcrumb: 'nav.help' })
const { t, locale } = useI18n()
const api = useApi()
const route = useRoute()
const { handle } = useErrorHandler()
const { setLabel } = useBreadcrumbs()

const category = computed(() => String(route.params.category) as HelpCategory)
const known = computed(() => (HELP_CATEGORIES as readonly string[]).includes(category.value))
const name = computed(() => (known.value ? t(`help.category.${category.value}.name`) : ''))
watchEffect(() => name.value && setLabel(`/help/${category.value}`, name.value))
useHead({ title: () => name.value || t('nav.help') })

const articles = ref<HelpArticleSummary[] | null>(null)
const faqs = ref<HelpFaq[]>([])
const failed = ref(false)
async function load() {
  if (!known.value) return
  failed.value = false
  try {
    const [list, questions] = await Promise.all([api.get<HelpArticleSummary[]>('/help/articles', { category: category.value, lang: locale.value }), api.get<HelpFaq[]>('/help/faqs', { category: category.value, lang: locale.value })])
    articles.value = list.data
    faqs.value = questions.data
  } catch (error) {
    failed.value = true
    handle(error, { silent: true })
  }
}
watch([category, locale], () => void load(), { immediate: true })
const faqLink = (faq: HelpFaq) => (faq.article && articles.value?.some(item => item.id === faq.article) ? helpArticlePath({ id: faq.article, category: category.value }) : null)
</script>

<template>
  <AppPanel id="help-category" :title="name || t('nav.help')" :subtitle="known ? t(`help.category.${category}.desc`) : undefined" :subtitle-icon="known ? HELP_CATEGORY_ICONS[category] : undefined">
    <template #actions>
      <UButton :label="t('help.back')" icon="i-lucide-circle-help" color="neutral" variant="outline" to="/help" />
    </template>

    <AppEmpty v-if="!known" icon="i-lucide-file-question" :title="t('help.notFound')" :actions="[{ label: t('help.back'), color: 'neutral', to: '/help' }]" />
    <AppEmpty v-else-if="failed && !articles" icon="i-lucide-cloud-alert" :title="t('dataView.errorTitle')" :actions="[{ label: t('common.retry'), icon: 'i-lucide-refresh-cw', color: 'neutral', variant: 'outline', onClick: load }]" />
    <div v-else-if="!articles" class="flex flex-col gap-2"><USkeleton v-for="n in 5" :key="n" class="h-14 w-full rounded-lg" /></div>
    <div v-else class="grid gap-4 lg:grid-cols-[minmax(0,3fr)_minmax(0,2fr)]">
      <UCard variant="outline" :ui="{ body: 'p-3 sm:p-4' }">
        <h2 class="px-1 text-sm font-semibold text-highlighted">{{ t('help.articles', { n: articles.length }, articles.length) }}</h2>
        <HelpArticleList :articles="articles" />
      </UCard>
      <UCard v-if="faqs.length" variant="outline" :ui="{ body: 'flex flex-col gap-2 p-4' }">
        <h2 class="text-sm font-semibold text-highlighted">{{ t('help.faq.title') }}</h2>
        <details v-for="faq in faqs" :key="faq.id" class="rounded-md border border-default px-3 py-2">
          <summary class="cursor-pointer list-none text-sm font-medium text-highlighted focus-visible:outline-2 focus-visible:outline-(--ui-border-inverted)">{{ faq.question }}</summary>
          <p class="mt-2 text-sm text-muted">{{ faq.answer }}</p>
          <UButton v-if="faqLink(faq)" :label="t('help.readMore')" color="neutral" variant="link" size="xs" class="mt-1 px-0" :to="faqLink(faq)!" />
        </details>
      </UCard>
    </div>
  </AppPanel>
</template>

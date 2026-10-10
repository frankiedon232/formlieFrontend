<!--
  What the help search found (F25): articles with the sentence that matched, FAQs (open in place) and glossary
  terms. Nothing found offers contacting support (the search is noted for the Formalie team).
-->
<script setup lang="ts">
import type { HelpSearchResult } from '#shared/types/help'
import { helpArticlePath } from '#shared/utils/help/categories'

const props = defineProps<{ result: HelpSearchResult | null; loading: boolean; supportEmail: string | null; categoryOf: (id: string) => string | undefined; showAnswer?: boolean }>()
const emit = defineEmits<{ clear: [] }>()
const { t } = useI18n()
const empty = computed(() => !!props.result && !props.result.articles.length && !props.result.faqs.length && !props.result.terms.length)
const articleLink = (id: string | null) => (id && props.categoryOf(id) ? helpArticlePath({ id, category: props.categoryOf(id) as never }) : null)
</script>

<template>
  <div class="flex flex-col gap-4" :aria-busy="loading || undefined">
    <div v-if="loading && !result" class="flex flex-col gap-2"><USkeleton v-for="n in 4" :key="n" class="h-14 w-full rounded-lg" /></div>
    <UCard v-else-if="empty" variant="outline" :ui="{ body: 'p-6' }">
      <AppEmpty
        icon="i-lucide-search-x"
        :title="t('help.search.none', { q: result!.query })"
        :description="t('help.search.noneDesc')"
        :actions="[{ label: t('help.search.clear'), color: 'neutral', variant: 'outline', onClick: () => emit('clear') }, ...(supportEmail ? [{ label: t('help.support.email'), icon: 'i-lucide-mail', color: 'neutral' as const, to: `mailto:${supportEmail}` }] : [])]"
      />
    </UCard>
    <template v-else-if="result">
      <UCard v-if="showAnswer && result.answer" variant="outline" class="ring-(--ui-border-accented)" :ui="{ body: 'flex flex-col gap-3 p-4 sm:p-5' }">
        <div class="flex flex-wrap items-center justify-between gap-2">
          <h2 class="flex items-center gap-1.5 text-sm font-semibold text-highlighted"><UIcon name="i-lucide-sparkles" class="size-4" />{{ t('help.answer.title') }}</h2>
          <UBadge :label="t('ai.label.made')" icon="i-lucide-sparkles" color="neutral" variant="soft" size="sm" class="rounded-md" />
        </div>
        <HelpBlocks :blocks="result.answer.blocks" compact />
        <p class="flex flex-wrap items-center gap-1 text-xs text-muted">
          {{ t('help.answer.from') }}
          <UButton :label="result.answer.article.title" color="neutral" variant="link" size="xs" class="px-0" :to="helpArticlePath(result.answer.article)" />
        </p>
      </UCard>
      <UCard v-if="result.articles.length" variant="outline" :ui="{ body: 'p-3 sm:p-4' }" :class="loading ? 'opacity-60' : ''">
        <h2 class="px-1 text-sm font-semibold text-highlighted">{{ t('help.search.articles') }}</h2>
        <HelpArticleList :articles="result.articles" show-area />
      </UCard>
      <UCard v-if="result.faqs.length" variant="outline" :ui="{ body: 'flex flex-col gap-2 p-4' }">
        <h2 class="text-sm font-semibold text-highlighted">{{ t('help.search.faqs') }}</h2>
        <details v-for="faq in result.faqs" :key="faq.id" class="group rounded-md border border-default px-3 py-2">
          <summary class="cursor-pointer list-none text-sm font-medium text-highlighted focus-visible:outline-2 focus-visible:outline-(--ui-border-inverted)">{{ faq.question }}</summary>
          <p class="mt-2 text-sm text-muted">{{ faq.answer }}</p>
          <UButton v-if="articleLink(faq.article)" :label="t('help.readMore')" color="neutral" variant="link" size="xs" class="mt-1 px-0" :to="articleLink(faq.article)!" />
        </details>
      </UCard>
      <UCard v-if="result.terms.length" variant="outline" :ui="{ body: 'flex flex-col gap-2 p-4' }">
        <h2 class="text-sm font-semibold text-highlighted">{{ t('help.search.terms') }}</h2>
        <dl class="grid gap-2 sm:grid-cols-2">
          <div v-for="term in result.terms" :key="term.id" class="flex flex-col gap-0.5 rounded-md border border-default px-3 py-2">
            <dt class="text-sm font-medium text-highlighted">{{ term.term }}</dt>
            <dd class="text-xs text-muted">{{ term.definition }}</dd>
          </div>
        </dl>
      </UCard>
    </template>
  </div>
</template>

<!--
  Ask about a form's responses in plain words (F19 M4): the answer as a number, the top answers with
  slim bars, or a trend; always with the period and filters it understood, so people can check it.
-->
<script setup lang="ts">
import type { AiAnswer } from '#shared/types/ai'
import { AI_KIND_META } from '#shared/utils/ai/kinds'

const props = defineProps<{ formId: string }>()
const { t, d } = useI18n()
const api = useApi()
const { handle } = useErrorHandler()
const { number } = useFormat()
const question = ref('')
const answer = ref<AiAnswer | null>(null)
const asking = ref(false)
watch(
  () => props.formId,
  () => (answer.value = null),
)
const examples = computed(() => [t('ai.ask.example.count'), t('ai.ask.example.top'), t('ai.ask.example.average'), t('ai.ask.example.trend')])
const day = (date: string) => d(new Date(`${date}T12:00:00`), { day: 'numeric', month: 'short', year: 'numeric' })
/** Trend rows: a month (2026-06) or a day in the reader's language; other labels as they are. */
const rowLabel = (label: string) => (/^\d{4}-\d{2}$/.test(label) ? d(new Date(`${label}-15T12:00:00`), { month: 'long', year: 'numeric' }) : /^\d{4}-\d{2}-\d{2}$/.test(label) ? day(label) : label)

async function ask() {
  if (asking.value || question.value.trim().length < 3) return
  asking.value = true
  try {
    answer.value = (await api.post<AiAnswer>('/ai/ask', { form_id: props.formId, question: question.value.trim() })).data
  } catch (error) {
    handle(error)
  } finally {
    asking.value = false
  }
}
const filterText = (filter: AiAnswer['filters'][number]) =>
  filter.kind === 'period' && answer.value?.period ? t('ai.range', { from: day(answer.value.period.from), to: day(answer.value.period.to) }) : filter.kind === 'status' ? t(`status.${filter.value}`) : `${filter.label}: ${filter.value}`
</script>

<template>
  <UCard variant="outline" :ui="{ body: 'flex flex-col gap-4 p-4 sm:p-5' }">
    <div class="flex flex-col gap-1">
      <h2 class="text-sm font-semibold text-highlighted">{{ t('ai.ask.title') }}</h2>
      <p class="text-xs text-muted">{{ t('ai.ask.desc') }}</p>
    </div>
    <form class="flex flex-col gap-2 sm:flex-row" @submit.prevent="ask">
      <UInput v-model="question" :placeholder="t('ai.ask.placeholder')" :maxlength="500" icon="i-lucide-message-circle-question" class="min-w-0 flex-1" :disabled="asking" :aria-label="t('ai.ask.title')" />
      <UButton type="submit" :label="t('ai.ask.button')" icon="i-lucide-sparkles" color="neutral" :loading="asking" :disabled="question.trim().length < 3" />
    </form>
    <div class="flex flex-wrap gap-1.5">
      <UButton v-for="example in examples" :key="example" :label="example" color="neutral" variant="outline" size="xs" class="max-w-full rounded-full" :ui="{ label: 'truncate' }" @click="(question = example), ask()" />
    </div>
    <p class="flex items-center gap-1.5 text-xs text-muted"><UIcon name="i-lucide-coins" class="size-3.5" />{{ t('ai.create.cost', { n: AI_KIND_META.question.credits }, AI_KIND_META.question.credits) }}</p>

    <div v-if="asking" class="flex flex-col gap-2"><USkeleton class="h-10 w-40" /><USkeleton class="h-24 w-full" /></div>
    <div v-else-if="answer" class="flex flex-col gap-3 rounded-lg border border-default p-4">
      <p class="text-xs text-muted">“{{ answer.question }}”</p>
      <div v-if="answer.kind === 'count' || answer.kind === 'average'" class="flex items-baseline gap-2">
        <span class="text-3xl font-semibold text-highlighted tabular-nums">{{ answer.value === null ? '–' : number(answer.value) }}</span>
        <span class="text-sm text-muted">{{ answer.kind === 'count' ? t('ai.ask.responses', { n: answer.value ?? 0 }, answer.value ?? 0) : t('ai.ask.averageOf', { label: answer.field?.label ?? '' }) }}</span>
      </div>
      <ul v-else-if="answer.rows.length" class="flex flex-col gap-2">
        <li v-if="answer.field" class="text-xs text-muted">{{ answer.kind === 'top' ? t('ai.ask.topOf', { label: answer.field.label, n: answer.value ?? 0 }) : t('ai.ask.trendOf', { label: answer.field.label }) }}</li>
        <li v-for="row in answer.rows" :key="row.label" class="flex flex-col gap-1">
          <div class="flex items-center justify-between gap-2 text-sm">
            <span class="truncate text-default">{{ rowLabel(row.label) }}</span>
            <span class="shrink-0 font-medium text-highlighted tabular-nums">{{ number(row.count) }}<span v-if="answer.kind === 'top'" class="ms-1 text-xs font-normal text-muted">{{ row.share }}%</span></span>
          </div>
          <UProgress :model-value="row.share" size="xs" color="neutral" />
        </li>
      </ul>
      <AppEmpty v-else size="xs" icon="i-lucide-search-x" :title="t('ai.note.no_answers')" />
      <div class="flex flex-wrap items-center gap-1.5 border-t border-default pt-3">
        <span class="text-xs text-muted">{{ t('ai.ask.filters') }}</span>
        <UBadge v-for="(filter, index) in answer.filters" :key="index" :label="filterText(filter)" color="neutral" variant="outline" size="sm" class="rounded-md" />
        <UBadge v-if="!answer.filters.length" :label="t('ai.ask.allResponses')" color="neutral" variant="outline" size="sm" class="rounded-md" />
      </div>
      <AiNotes v-if="answer.notes.length" :notes="answer.notes" />
    </div>
  </UCard>
</template>

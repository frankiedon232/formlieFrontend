<!--
  What a form's responses say (F19 M4), in the design's style: two chart cards (responses with the change
  and per day; tone as thin lines), what stands out, themes in written answers (share bar, tone, examples),
  average ratings against the period before and the most chosen answers. Used by Response analysis and
  Insights & summaries.
-->
<script setup lang="ts">
import type { AiAnalysis } from '#shared/types/ai'

const props = defineProps<{ analysis: AiAnalysis }>()
const { t, d } = useI18n()
const { number } = useFormat()
const day = (date: string) => d(new Date(`${date}T12:00:00`), { day: 'numeric', month: 'short' })

const change = computed(() => (props.analysis.totals.previous ? Math.round(((props.analysis.totals.responses - props.analysis.totals.previous) / props.analysis.totals.previous) * 100) : null))
const toneTotal = computed(() => props.analysis.sentiment.positive + props.analysis.sentiment.neutral + props.analysis.sentiment.negative)
const positiveShare = computed(() => (toneTotal.value ? Math.round((props.analysis.sentiment.positive / toneTotal.value) * 100) : 0))
const stats = computed(() => [
  { label: t('ai.analysis.written'), value: number(props.analysis.totals.text_answers) },
  { label: t('ai.analysis.positive'), value: `${positiveShare.value}%` },
  { label: t('ai.analysis.before'), value: number(props.analysis.totals.previous) },
])
const tone = computed(() => [
  { key: 'positive', label: t('ai.tone.positive'), count: props.analysis.sentiment.positive, color: 'bg-green-500' },
  { key: 'neutral', label: t('ai.tone.neutral'), count: props.analysis.sentiment.neutral, color: 'bg-(--ui-text-muted)' },
  { key: 'negative', label: t('ai.tone.negative'), count: props.analysis.sentiment.negative, color: 'bg-red-500' },
])
const open = ref<string | null>(null)
</script>

<template>
  <div class="flex flex-col gap-4">
    <div class="grid gap-4 lg:grid-cols-2">
      <UCard variant="outline" :ui="{ body: 'flex h-full flex-col gap-4 p-4 sm:p-5' }">
        <div class="flex items-start justify-between gap-2">
          <div class="flex flex-col">
            <h2 class="text-sm font-semibold text-highlighted">{{ t('ai.analysis.responsesTitle') }}</h2>
            <span class="text-xs text-muted">{{ t('ai.range', { from: day(analysis.period.from), to: day(analysis.period.to) }) }}</span>
          </div>
          <UBadge :label="t('ai.label.made')" icon="i-lucide-sparkles" color="neutral" variant="soft" size="sm" class="rounded-md" />
        </div>
        <div class="flex flex-1 items-end gap-5">
          <div class="flex shrink-0 flex-col gap-3">
            <div class="flex items-center gap-2.5">
              <UIcon name="i-lucide-inbox" class="size-5 text-muted" />
              <span class="text-3xl leading-none font-semibold text-highlighted tabular-nums">{{ number(analysis.totals.responses) }}</span>
              <div class="flex flex-col gap-0.5">
                <UBadge v-if="change !== null" :label="`${change > 0 ? '+' : ''}${change}%`" :color="change >= 0 ? 'success' : 'error'" variant="subtle" size="sm" class="w-fit rounded-md tabular-nums" />
                <span class="text-[11px] text-muted">{{ t('responses.overview.vsBefore') }}</span>
              </div>
            </div>
            <dl class="flex gap-4">
              <div v-for="stat in stats" :key="stat.label" class="flex min-w-0 flex-col">
                <dt class="truncate text-[11px] text-muted">{{ stat.label }}</dt>
                <dd class="truncate text-sm font-medium text-highlighted tabular-nums">{{ stat.value }}</dd>
              </div>
            </dl>
          </div>
          <ChartsMiniBars :days="analysis.daily" :label="t('ai.analysis.perDay')" />
        </div>
      </UCard>

      <UCard variant="outline" :ui="{ body: 'flex h-full flex-col gap-4 p-4 sm:p-5' }">
        <div class="flex items-start justify-between gap-2">
          <h2 class="text-sm font-semibold text-highlighted">{{ t('ai.analysis.tone') }}</h2>
          <span class="text-xs text-muted">{{ t('ai.analysis.writtenCount', { n: number(analysis.totals.text_answers) }, analysis.totals.text_answers) }}</span>
        </div>
        <AppEmpty v-if="!toneTotal" size="xs" icon="i-lucide-message-square-off" :title="t('ai.note.no_text')" />
        <div v-else class="flex flex-1 items-end gap-6">
          <ChartsLines :parts="tone" class="min-w-0 flex-1" />
          <ul class="hidden shrink-0 flex-col gap-1 sm:flex">
            <li v-for="part in tone" :key="part.key" class="flex items-center gap-2 px-1.5 py-0.5 text-xs">
              <span class="size-2 shrink-0 rounded-[2px]" :class="part.color" />
              <span class="w-20 truncate text-default">{{ part.label }}</span>
              <span class="ms-auto font-medium text-highlighted tabular-nums">{{ number(part.count) }}</span>
            </li>
          </ul>
        </div>
      </UCard>
    </div>

    <UCard v-if="analysis.findings.length" variant="outline" :ui="{ body: 'flex flex-col gap-3 p-4 sm:p-5' }">
      <h2 class="text-sm font-semibold text-highlighted">{{ t('ai.analysis.standsOut') }}</h2>
      <AiNotes :notes="analysis.findings" />
    </UCard>

    <div class="grid gap-4 lg:grid-cols-[minmax(0,3fr)_minmax(0,2fr)]">
      <UCard variant="outline" :ui="{ body: 'flex flex-col gap-3 p-4 sm:p-5' }">
        <h2 class="text-sm font-semibold text-highlighted">{{ t('ai.analysis.themes') }}</h2>
        <AppEmpty v-if="!analysis.themes.length" size="xs" icon="i-lucide-message-square-off" :title="t('ai.note.no_text')" />
        <ul v-else class="flex flex-col divide-y divide-default">
          <li v-for="theme in analysis.themes" :key="theme.key" class="py-2.5">
            <button type="button" class="flex w-full flex-col gap-1.5 rounded-md text-start focus-visible:outline-2 focus-visible:outline-(--ui-border-inverted)" :aria-expanded="open === theme.key" @click="open = open === theme.key ? null : theme.key">
              <span class="flex items-center gap-2">
                <span class="min-w-0 flex-1 truncate text-sm font-medium text-highlighted">{{ t(`ai.theme.${theme.key}`) }}</span>
                <UBadge v-if="theme.positive" :label="`+${theme.positive}`" color="success" variant="subtle" size="sm" class="rounded-md tabular-nums" />
                <UBadge v-if="theme.negative" :label="`−${theme.negative}`" color="error" variant="subtle" size="sm" class="rounded-md tabular-nums" />
                <span class="w-10 text-end text-xs text-muted tabular-nums">{{ theme.share }}%</span>
                <UIcon :name="open === theme.key ? 'i-lucide-chevron-up' : 'i-lucide-chevron-down'" class="size-4 text-muted" />
              </span>
              <UProgress :model-value="theme.share" size="xs" color="neutral" />
            </button>
            <ul v-if="open === theme.key" class="mt-2 flex flex-col gap-1.5">
              <li v-for="(example, index) in theme.examples" :key="index" class="border-s-2 border-default ps-3 text-sm text-muted italic">“{{ example }}”</li>
            </ul>
          </li>
        </ul>
      </UCard>

      <div class="flex flex-col gap-4">
        <UCard v-if="analysis.ratings.length" variant="outline" :ui="{ body: 'flex flex-col gap-3 p-4 sm:p-5' }">
          <h2 class="text-sm font-semibold text-highlighted">{{ t('ai.analysis.ratings') }}</h2>
          <div v-for="rating in analysis.ratings" :key="rating.key" class="flex flex-col gap-1">
            <div class="flex items-center justify-between gap-2 text-sm">
              <span class="truncate text-default">{{ rating.label }}</span>
              <span class="flex shrink-0 items-center gap-1.5 tabular-nums">
                <span class="font-medium text-highlighted">{{ rating.average }} / {{ rating.max }}</span>
                <span v-if="rating.previous !== null" class="text-xs text-muted">{{ t('ai.analysis.was', { n: rating.previous }) }}</span>
              </span>
            </div>
            <UProgress :model-value="Math.round((rating.average / rating.max) * 100)" size="xs" color="neutral" />
          </div>
        </UCard>
        <UCard v-if="analysis.choices.length" variant="outline" :ui="{ body: 'flex flex-col gap-3 p-4 sm:p-5' }">
          <h2 class="text-sm font-semibold text-highlighted">{{ t('ai.analysis.mostChosen') }}</h2>
          <dl class="grid gap-3 sm:grid-cols-2">
            <div v-for="choice in analysis.choices" :key="choice.key" class="flex min-w-0 flex-col gap-0.5 rounded-lg border border-default px-3 py-2">
              <dt class="truncate text-[11px] text-muted">{{ choice.label }}</dt>
              <dd class="truncate text-sm font-medium text-highlighted">{{ choice.top }} <span class="text-xs font-normal text-muted tabular-nums">· {{ choice.share }}%</span></dd>
            </div>
          </dl>
        </UCard>
      </div>
    </div>
  </div>
</template>

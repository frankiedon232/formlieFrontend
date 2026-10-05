<!--
  One question's summary (F11 Summary tab): how many answered it, then by kind, choices as slim
  bars (most picked first and emphasised), ratings as the average with a small distribution,
  numbers as average · median · range, text as the latest answers (each opens its response).
-->
<script setup lang="ts">
import type { QuestionInsight } from '#shared/types/responses'
import { FIELD_TYPES } from '#shared/utils/forms/fields'

const props = defineProps<{ question: QuestionInsight; index: number; total: number }>()
const emit = defineEmits<{ open: [id: string] }>()
const { t } = useI18n()
const { number, percent, relative } = useFormat()

const icon = computed(() => (FIELD_TYPES as Record<string, { icon: string }>)[props.question.type]?.icon ?? 'i-lucide-circle-help')
const choices = computed(() => {
  const q = props.question
  if (q.kind !== 'choice') return []
  const named = q.options.map(option => ({ ...option, label: q.type === 'toggle' ? t(option.value === 'true' ? 'responses.answer.yes' : 'responses.answer.no') : option.label || option.value }))
  return [...named].sort((a, b) => b.count - a.count)
})
/** Net Promoter Score for a 0 to 10 scale: promoters (9, 10) minus detractors (0 to 6), in points. */
const nps = computed(() => {
  const q = props.question
  if (q.kind !== 'rating' || q.min !== 0 || q.max !== 10 || !q.answered) return null
  const count = (from: number, to: number) => q.distribution.filter(item => item.value >= from && item.value <= to).reduce((sum, item) => sum + item.count, 0)
  const all = count(0, 10) || 1
  const parts = [
    { key: 'detractors', share: count(0, 6) / all, color: 'bg-error' },
    { key: 'passives', share: count(7, 8) / all, color: 'bg-warning' },
    { key: 'promoters', share: count(9, 10) / all, color: 'bg-success' },
  ]
  return { score: Math.round((parts[2]!.share - parts[0]!.share) * 100), parts }
})
const top = computed(() => Math.max(1, ...(props.question.kind === 'rating' ? props.question.distribution.map(item => item.count) : [1])))
</script>

<template>
  <UCard variant="outline" :ui="{ body: 'flex h-full flex-col gap-4 p-4 sm:p-5' }">
    <div class="flex items-start gap-3">
      <span class="flex size-8 shrink-0 items-center justify-center rounded-md bg-elevated text-muted">
        <UIcon :name="icon" class="size-4" />
      </span>
      <div class="flex min-w-0 flex-1 flex-col gap-0.5">
        <h3 class="text-sm font-medium text-highlighted">
          <span class="me-1 text-dimmed tabular-nums">{{ index + 1 }}.</span>{{ question.label }}
        </h3>
        <p class="text-xs text-muted">
          {{ t('responses.summary.answered', { n: number(question.answered), share: percent(total ? question.answered / total : 0) }) }}
          <template v-if="question.kind === 'choice' && question.multiple"> · {{ t('responses.summary.multiple') }}</template>
        </p>
      </div>
    </div>

    <div v-if="!question.answered" class="text-sm text-muted">{{ t('responses.summary.none') }}</div>

    <div v-else-if="question.kind === 'choice'" class="flex flex-col gap-3">
      <ChartsMeter v-for="(choice, i) in choices.slice(0, 8)" :key="choice.value" :label="choice.label" :count="choice.count" :total="question.answered" :strong="i === 0" />
      <p v-if="choices.length > 8" class="text-xs text-muted">{{ t('responses.summary.more', { n: choices.length - 8 }) }}</p>
    </div>

    <div v-else-if="question.kind === 'rating'" class="flex flex-col gap-3">
      <div class="flex items-end gap-5">
        <div class="flex shrink-0 flex-col">
          <span class="text-3xl leading-none font-semibold text-highlighted tabular-nums">{{ number(question.average) }}</span>
          <span class="mt-1 text-xs text-muted">{{ t('responses.summary.outOf', { max: question.max }) }}</span>
        </div>
        <div class="flex h-20 min-w-0 flex-1 items-end gap-1" role="list">
          <div v-for="item in question.distribution" :key="item.value" role="listitem" class="flex h-full min-w-0 flex-1 flex-col items-center justify-end gap-1" :aria-label="`${item.value}: ${number(item.count)}`">
            <div class="w-full rounded-t-[4px] bg-inverted" :style="{ height: `${(item.count / top) * 100}%`, minHeight: item.count ? '2px' : '0', opacity: 0.35 + 0.65 * (item.count / top) }" />
            <span class="text-[10px] text-muted tabular-nums">{{ item.value }}</span>
          </div>
        </div>
      </div>
      <div v-if="nps" class="flex flex-col gap-2 border-t border-default pt-3">
        <div class="flex items-baseline justify-between gap-2">
          <span class="text-xs text-muted">{{ t('responses.summary.nps') }}</span>
          <span class="text-lg leading-none font-semibold text-highlighted tabular-nums">{{ nps.score > 0 ? '+' : '' }}{{ nps.score }}</span>
        </div>
        <div class="flex h-1.5 gap-0.5 overflow-hidden rounded-full" role="presentation">
          <span v-for="part in nps.parts" :key="part.key" :class="part.color" :style="{ width: `${part.share * 100}%` }" />
        </div>
        <div class="flex flex-wrap gap-x-3 gap-y-1 text-[11px] text-muted">
          <span v-for="part in nps.parts" :key="part.key" class="flex items-center gap-1"><span class="size-1.5 rounded-full" :class="part.color" />{{ t(`responses.summary.${part.key}`) }} {{ percent(part.share) }}</span>
        </div>
      </div>
    </div>

    <div v-else-if="question.kind === 'number'" class="flex flex-col gap-3">
      <dl class="grid grid-cols-4 gap-2">
        <div v-for="stat in (['average', 'median', 'min', 'max'] as const)" :key="stat" class="flex flex-col gap-0.5">
          <dt class="text-[11px] text-muted uppercase">{{ t(`responses.summary.${stat}`) }}</dt>
          <dd class="truncate text-sm font-semibold text-highlighted tabular-nums">{{ number(question[stat], { maximumFractionDigits: 2 }) }}</dd>
        </div>
      </dl>
      <!-- Where the average sits in the range. -->
      <div class="relative h-1.5 rounded-full bg-elevated" role="presentation">
        <span
          class="absolute top-1/2 size-3 -translate-y-1/2 rounded-full border-2 border-default bg-inverted"
          :style="{ insetInlineStart: `calc(${question.max > question.min ? ((question.average - question.min) / (question.max - question.min)) * 100 : 50}% - 6px)` }"
        />
      </div>
    </div>

    <ul v-else-if="question.kind === 'text'" class="flex flex-col divide-y divide-default">
      <li v-for="item in question.latest" :key="item.id">
        <button type="button" class="group flex w-full flex-col gap-0.5 py-2 text-start first:pt-0 focus-visible:outline-2 focus-visible:outline-(--ui-border-inverted)" @click="emit('open', item.id)">
          <span class="line-clamp-2 text-sm text-default group-hover:text-highlighted">“{{ item.value }}”</span>
          <span class="text-[11px] text-dimmed">{{ relative(item.at) }}</span>
        </button>
      </li>
    </ul>

    <p v-else class="text-sm text-muted">{{ t('responses.summary.inTable') }}</p>
  </UCard>
</template>

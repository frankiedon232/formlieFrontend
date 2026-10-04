<!--
  Responses headline numbers (F11), in the design's KPI card style (docs/design 092034): title,
  icon · big number · trend badge, a caption, and a flat sparkline or slim meter for the shape.
  Responses in the period (vs the period before) · to review · median time · completion (per form)
  or last response (inbox). "To review" filters the list to new responses.
-->
<script setup lang="ts">
import type { ResponseInsights } from '#shared/types/responses'

const props = defineProps<{ insights: ResponseInsights; perForm?: boolean }>()
const emit = defineEmits<{ review: [] }>()
const { t } = useI18n()
const { number, percent, relative } = useFormat()
const { duration } = useResponseFormat()

const trend = computed(() => {
  const { count, previous } = props.insights.period
  return previous ? Math.round(((count - previous) / previous) * 100) : null
})
const daily = computed(() => props.insights.daily.map(day => day.count))
const cards = computed(() => [
  {
    key: 'period',
    title: t('responses.kpi.period'),
    icon: 'i-lucide-inbox',
    value: number(props.insights.period.count),
    trend: trend.value,
    caption: t('responses.kpi.total', { n: number(props.insights.total) }),
    spark: daily.value,
  },
  {
    key: 'new',
    title: t('responses.kpi.toReview'),
    icon: 'i-lucide-sparkle',
    value: number(props.insights.new),
    trend: null,
    caption: props.insights.total ? t('responses.kpi.ofAll', { share: percent(props.insights.new / props.insights.total) }) : t('responses.kpi.nothing'),
    meter: props.insights.total ? props.insights.new / props.insights.total : 0,
    action: props.insights.new ? t('responses.kpi.review') : null,
  },
  {
    key: 'time',
    title: t('responses.kpi.time'),
    icon: 'i-lucide-timer',
    value: props.insights.median_seconds != null ? duration(Math.round(props.insights.median_seconds)) : '-',
    trend: null,
    caption: t('responses.kpi.timeHint'),
  },
  props.perForm
    ? {
        key: 'completion',
        title: t('responses.kpi.completion'),
        icon: 'i-lucide-circle-check-big',
        value: props.insights.completion_rate != null ? `${props.insights.completion_rate}%` : '-',
        trend: null,
        caption: t('responses.kpi.completionHint'),
        meter: (props.insights.completion_rate ?? 0) / 100,
      }
    : {
        key: 'last',
        title: t('responses.kpi.last'),
        icon: 'i-lucide-clock-3',
        value: props.insights.last_at ? relative(props.insights.last_at) : '-',
        trend: null,
        caption: props.insights.top_forms[0] ? t('responses.kpi.busiest', { name: props.insights.top_forms[0].name }) : t('responses.kpi.nothing'),
      },
])
</script>

<template>
  <div class="grid grid-cols-2 gap-3 xl:grid-cols-4">
    <UCard v-for="card in cards" :key="card.key" variant="outline" :ui="{ body: 'flex h-full flex-col gap-3 p-3 sm:p-4' }">
      <div class="flex items-start justify-between gap-2">
        <h3 class="truncate text-sm font-medium text-highlighted">{{ card.title }}</h3>
        <UButton v-if="card.action" :label="card.action" :aria-label="card.action" trailing-icon="i-lucide-arrow-right" color="neutral" variant="link" size="xs" :ui="{ label: 'hidden sm:inline' }" class="-me-1.5 rtl:[&_svg]:rotate-180" @click="emit('review')" />
      </div>
      <div class="flex items-end justify-between gap-3">
        <div class="flex min-w-0 items-center gap-2.5">
          <UIcon :name="card.icon" class="hidden size-5 shrink-0 text-muted sm:block" />
          <span class="text-xl leading-none font-semibold whitespace-nowrap text-highlighted tabular-nums sm:text-2xl">{{ card.value }}</span>
          <UBadge
            v-if="card.trend !== null"
            :label="`${card.trend > 0 ? '+' : ''}${card.trend}%`"
            :color="card.trend >= 0 ? 'success' : 'error'"
            variant="subtle"
            size="sm"
            class="rounded-md tabular-nums"
          />
        </div>
        <ChartsSparkline v-if="card.spark" :values="card.spark" class="hidden sm:block" />
      </div>
      <div v-if="card.meter !== undefined" class="h-1 overflow-hidden rounded-full bg-elevated" role="presentation">
        <div class="h-full rounded-full bg-inverted" :style="{ width: `${Math.min(100, card.meter * 100)}%` }" />
      </div>
      <p class="mt-auto truncate text-xs text-muted">{{ card.caption }}</p>
    </UCard>
  </div>
</template>

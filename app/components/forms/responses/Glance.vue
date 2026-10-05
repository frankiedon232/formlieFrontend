<!--
  Insights → At a glance (F11; owner 2026-10-05: the all-forms Insights must not be one-sided): six
  tiles in two columns beside Responses over time, the same height: responses in the period (with
  its change), per day, the busiest day, the median time to fill in, still to review, and all time.
-->
<script setup lang="ts">
import type { ResponseInsights } from '#shared/types/responses'

const props = defineProps<{ insights: ResponseInsights }>()
const { t, d } = useI18n()
const { number, percent } = useFormat()
const { duration } = useResponseFormat()

const trend = computed(() => {
  const { count, previous } = props.insights.period
  return previous ? Math.round(((count - previous) / previous) * 100) : null
})
const busiest = computed(() => props.insights.daily.reduce<{ date: string; count: number } | null>((top, day) => (!top || day.count > top.count ? day : top), null))
const tiles = computed(() => [
  { key: 'period', icon: 'i-lucide-inbox', label: t('responses.glance.inPeriod'), value: number(props.insights.period.count), hint: trend.value === null ? '' : `${trend.value > 0 ? '+' : ''}${trend.value}%`, good: (trend.value ?? 0) >= 0 },
  { key: 'perDay', icon: 'i-lucide-calendar-days', label: t('responses.glance.perDay'), value: number(Math.round((props.insights.period.count / Math.max(1, props.insights.daily.length)) * 10) / 10), hint: '' },
  {
    key: 'busiest',
    icon: 'i-lucide-flame',
    label: t('responses.glance.busiestDay'),
    value: busiest.value?.count ? d(new Date(`${busiest.value.date}T12:00:00`), { day: 'numeric', month: 'short' }) : '–',
    hint: busiest.value?.count ? number(busiest.value.count) : '',
  },
  { key: 'time', icon: 'i-lucide-timer', label: t('responses.kpi.time'), value: duration(props.insights.median_seconds) || '–', hint: '' },
  { key: 'review', icon: 'i-lucide-sparkle', label: t('responses.kpi.toReview'), value: number(props.insights.new), hint: props.insights.total ? percent(props.insights.new / props.insights.total) : '' },
  { key: 'total', icon: 'i-lucide-archive', label: t('responses.kpi.totalLabel'), value: number(props.insights.total), hint: '' },
])
</script>

<template>
  <UCard variant="outline" :ui="{ root: 'h-full', body: 'flex h-full flex-col gap-4 p-4 sm:p-5' }">
    <h2 class="text-sm font-semibold text-highlighted">{{ t('responses.kpi.label') }}</h2>
    <dl class="grid flex-1 grid-cols-2 gap-2">
      <div v-for="tile in tiles" :key="tile.key" class="flex min-w-0 flex-col justify-between gap-2 rounded-lg border border-default p-3">
        <dt class="flex items-center gap-1.5 text-xs text-muted">
          <UIcon :name="tile.icon" class="size-3.5 shrink-0" />
          <span class="truncate">{{ tile.label }}</span>
        </dt>
        <dd class="flex min-w-0 items-baseline gap-1.5">
          <span class="truncate text-lg leading-none font-semibold text-highlighted tabular-nums">{{ tile.value }}</span>
          <UBadge v-if="tile.key === 'period' && tile.hint" :label="tile.hint" :color="tile.good ? 'success' : 'error'" variant="subtle" size="sm" class="rounded-md tabular-nums" />
          <span v-else-if="tile.hint" class="truncate text-xs text-muted tabular-nums">{{ tile.hint }}</span>
        </dd>
      </div>
    </dl>
  </UCard>
</template>

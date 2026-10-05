<!--
  Insights → Busiest days of the week (F11; owner 2026-10-05): the average number of responses per
  weekday in the chosen period, Monday first, as the same slim columns as Responses over time; the
  busiest day is named above. Worked out from the daily counts, so no extra request.
-->
<script setup lang="ts">
import type { ResponseInsights } from '#shared/types/responses'

const props = defineProps<{ insights: ResponseInsights }>()
const { t, d } = useI18n()
const { number } = useFormat()

/** 0 = Monday … 6 = Sunday. */
const weekday = (date: string) => (new Date(`${date}T12:00:00Z`).getUTCDay() + 6) % 7
const points = computed(() => {
  const sums = Array.from({ length: 7 }, () => ({ total: 0, days: 0 }))
  for (const day of props.insights.daily) {
    const slot = sums[weekday(day.date)]!
    slot.total += day.count
    slot.days += 1
  }
  // 2024-01-01 was a Monday: name each weekday in the person's language.
  return sums.map((slot, index) => ({
    label: d(new Date(Date.UTC(2024, 0, 1 + index, 12)), { weekday: 'short' }),
    value: slot.days ? Math.round((slot.total / slot.days) * 10) / 10 : 0,
    hint: d(new Date(Date.UTC(2024, 0, 1 + index, 12)), { weekday: 'long' }),
  }))
})
const top = computed(() => points.value.reduce((best, point) => (point.value > best.value ? point : best), points.value[0]!))
const unit = (n: number) => t('responses.weekdays.unit', { n: number(n) })
</script>

<template>
  <UCard variant="outline" :ui="{ root: 'h-full', body: 'flex h-full flex-col gap-4 p-4 sm:p-5' }">
    <div class="flex flex-wrap items-start justify-between gap-2">
      <div class="flex flex-col gap-1">
        <h2 class="text-sm font-semibold text-highlighted">{{ t('responses.weekdays.title') }}</h2>
        <p class="text-xs text-muted">{{ t('responses.weekdays.desc') }}</p>
      </div>
      <UBadge v-if="top.value" :label="t('responses.weekdays.top', { day: top.hint })" icon="i-lucide-flame" color="neutral" variant="outline" size="sm" />
    </div>
    <ChartsBars :points="points" :unit="unit" height="h-40" class="mt-auto" />
  </UCard>
</template>

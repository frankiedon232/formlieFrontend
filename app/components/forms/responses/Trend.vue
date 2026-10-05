<!--
  Responses over time (F11): the period's total with its change against the period before, and a
  slim column chart by day or by week (segmented control, docs/design "Daily / Weekly").
-->
<script setup lang="ts">
import type { ResponseInsights } from '#shared/types/responses'

const props = defineProps<{ insights: ResponseInsights }>()
const { t, d } = useI18n()
const { number } = useFormat()

const step = ref<'day' | 'week'>('day')
const steps = computed(() => [
  { value: 'day', label: t('responses.trend.daily') },
  { value: 'week', label: t('responses.trend.weekly') },
])
const day = (date: string) => d(new Date(`${date}T12:00:00`), { day: 'numeric', month: 'short' })
const points = computed(() => {
  const days = props.insights.daily
  if (step.value === 'day') return days.map(item => ({ label: day(item.date), value: item.count }))
  const weeks: { label: string; value: number; hint: string }[] = []
  for (let i = 0; i < days.length; i += 7) {
    const chunk = days.slice(i, i + 7)
    weeks.push({ label: day(chunk[0]!.date), value: chunk.reduce((sum, item) => sum + item.count, 0), hint: `${day(chunk[0]!.date)} → ${day(chunk[chunk.length - 1]!.date)}` })
  }
  return weeks
})
const trend = computed(() => {
  const { count, previous } = props.insights.period
  return previous ? Math.round(((count - previous) / previous) * 100) : null
})
const perDay = computed(() => (props.insights.daily.length ? props.insights.period.count / props.insights.daily.length : 0))
const unit = (n: number) => t('responses.count', { n: number(n) }, n)
</script>

<template>
  <UCard variant="outline" :ui="{ body: 'flex flex-col gap-4 p-4 sm:p-5' }">
    <div class="flex flex-wrap items-start justify-between gap-3">
      <div class="flex flex-col gap-1">
        <h2 class="text-sm font-semibold text-highlighted">{{ t('responses.trend.title') }}</h2>
        <div class="flex items-center gap-2">
          <span class="text-2xl leading-none font-semibold text-highlighted tabular-nums">{{ number(insights.period.count) }}</span>
          <UBadge v-if="trend !== null" :label="`${trend > 0 ? '+' : ''}${trend}%`" :color="trend >= 0 ? 'success' : 'error'" variant="subtle" size="sm" class="rounded-md tabular-nums" />
        </div>
        <p class="text-xs text-muted">{{ t('responses.trend.perDay', { n: number(perDay, { maximumFractionDigits: 1 }) }) }}</p>
      </div>
      <UTabs v-model="step" :items="steps" :content="false" color="neutral" size="xs" :ui="SEGMENTED_UI" :aria-label="t('responses.trend.step')" />
    </div>
    <ChartsBars v-if="insights.period.count" :points="points" :unit="unit" />
    <AppEmpty v-else icon="i-lucide-chart-column" :title="t('responses.trend.empty')" :description="t('responses.trend.emptyDesc')" variant="naked" size="sm" />
  </UCard>
</template>

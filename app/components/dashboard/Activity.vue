<!--
  Dashboard → Activity overview (F21, the design's "Productivity Overview"): responses in the period with the change
  from the period before and the average per day, then the two-line chart (started above, sent below, the gap
  hatched) by the chosen group (day, week, month, year) with a tooltip: completion, responses, started, API calls.
-->
<script setup lang="ts">
import type { DashboardGroup, WorkspaceDashboard } from '#shared/types/dashboard'

const props = defineProps<{ data: WorkspaceDashboard | null }>()
const { t, d } = useI18n()
const { number } = useFormat()

const active = ref<number | null>(null)
watch(() => props.data, () => (active.value = null))
const series = computed(() => props.data?.series ?? [])
const label = (start: string, group: DashboardGroup) => {
  const date = new Date(`${start}T00:00:00Z`)
  if (group === 'year') return String(date.getUTCFullYear())
  if (group === 'month') return d(date, { month: 'short', year: '2-digit', timeZone: 'UTC' })
  return d(date, { day: 'numeric', month: 'short', timeZone: 'UTC' })
}
const points = computed(() => series.value.map(point => ({ label: label(point.start, props.data!.group), upper: point.starts, lower: point.responses })))
const total = computed(() => props.data?.kpis.responses.value ?? 0)
const change = computed(() => {
  const kpi = props.data?.kpis.responses
  return kpi?.previous ? Math.round(((kpi.value - kpi.previous) / kpi.previous) * 100) : null
})
const days = computed(() => (props.data ? Math.round((Date.parse(props.data.to) - Date.parse(props.data.from)) / 86_400_000) + 1 : 1))
const rate = (index: number) => {
  const point = series.value[index]
  return point?.starts ? Math.round((point.responses / point.starts) * 1000) / 10 : 0
}
const anyApi = computed(() => series.value.some(point => point.api_calls))
</script>

<template>
  <UCard variant="outline" class="flex h-full min-w-0 flex-col" :ui="{ body: 'flex h-full flex-col gap-4 p-4 sm:p-5' }">
    <div class="flex flex-wrap items-start justify-between gap-3">
      <div class="flex flex-col gap-1">
        <h2 class="text-sm font-semibold text-highlighted">{{ t('dashboard.activity.title') }}</h2>
        <div v-if="data" class="flex items-center gap-3 border-s-2 border-default ps-3">
          <span class="flex flex-col">
            <span class="flex items-center gap-2">
              <span class="text-2xl font-semibold text-highlighted tabular-nums">{{ t('dashboard.activity.responses', { n: number(total) }, total) }}</span>
              <UBadge v-if="change !== null" :label="`${change >= 0 ? '+' : ''}${change}%`" :color="change >= 0 ? 'success' : 'error'" variant="subtle" size="sm" />
            </span>
            <span class="text-xs text-muted">{{ t('dashboard.activity.perDay', { n: number(total / days, { maximumFractionDigits: 1 }) }) }}</span>
          </span>
        </div>
        <USkeleton v-else class="h-12 w-56" />
      </div>
    </div>

    <USkeleton v-if="!data" class="h-64 w-full" />
    <AppEmpty v-else-if="!total && !anyApi" size="sm" icon="i-lucide-chart-spline" :title="t('dashboard.activity.none')" :description="t('dashboard.activity.noneDesc')" :actions="[{ label: t('dashboard.newForm'), icon: 'i-lucide-plus', color: 'neutral', to: '/forms/new' }]" />
    <ChartsFlow v-else v-model:active="active" :points="points" :upper-label="t('analytics.started')" :lower-label="t('dashboard.activity.sent')">
      <template #tooltip="{ index }">
        <div class="flex items-center gap-2">
          <span class="text-xl leading-none font-semibold text-highlighted tabular-nums">{{ number(rate(index), { maximumFractionDigits: 1 }) }}%</span>
        </div>
        <p class="mt-1 truncate text-xs text-muted">{{ t('dashboard.activity.completion') }} · {{ points[index]?.label }}</p>
        <div class="mt-3 grid grid-cols-2 gap-x-6 gap-y-2 border-t border-default pt-3 text-xs">
          <span class="flex flex-col"><span class="flex items-center gap-1.5 text-muted"><span class="size-2 rounded-full bg-success" />{{ t('dashboard.activity.sent') }}</span><span class="text-base font-semibold text-highlighted tabular-nums">{{ number(series[index]?.responses ?? 0) }}</span></span>
          <span class="flex flex-col"><span class="flex items-center gap-1.5 text-muted"><span class="size-2 rounded-full bg-(--ui-text-muted)" />{{ t('analytics.started') }}</span><span class="text-base font-semibold text-highlighted tabular-nums">{{ number(series[index]?.starts ?? 0) }}</span></span>
          <span v-if="anyApi" class="col-span-2 flex items-center gap-1.5 text-muted"><UIcon name="i-lucide-code-xml" class="size-3.5" />{{ t('dashboard.activity.apiCalls', { n: number(series[index]?.api_calls ?? 0) }) }}</span>
        </div>
      </template>
    </ChartsFlow>

    <div v-if="data && (total || anyApi)" class="mt-auto flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-muted">
      <span class="flex items-center gap-1.5"><span class="size-2 rounded-full bg-(--ui-text-muted)" />{{ t('analytics.started') }}</span>
      <span class="flex items-center gap-1.5"><span class="size-2 rounded-full bg-success" />{{ t('dashboard.activity.sent') }}</span>
      <span class="flex items-center gap-1.5"><span class="h-2 w-3 rounded-sm bg-[repeating-linear-gradient(45deg,var(--ui-border-accented)_0_2px,transparent_2px_5px)]" />{{ t('analytics.conversion.left') }}</span>
    </div>
  </UCard>
</template>

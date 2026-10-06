<!--
  API traffic (F13 M4, the design's overview chart): calls in the period with their change, and the
  flow chart of all calls vs the ones that worked; the hatched gap is the calls that were refused or
  failed. The tooltip gives the day's error share and both counts.
-->
<script setup lang="ts">
import type { ApiAnalytics } from '#shared/types/apiService'

const props = defineProps<{ analytics: ApiAnalytics | null; change: number | null }>()
const { t, d } = useI18n()
const { number, percent } = useFormat()
const at = (date: string) => new Date(`${date}T12:00:00`)
const points = computed(() => (props.analytics?.daily ?? []).map(day => ({ label: d(at(day.date), { day: 'numeric', month: 'short' }), upper: day.calls, lower: Math.max(0, day.calls - day.errors) })))
const active = ref<number | null>(null)
watch(() => props.analytics, () => (active.value = null))
const perDay = computed(() => (props.analytics?.daily.length ? props.analytics.totals.calls / props.analytics.daily.length : 0))
</script>

<template>
  <UCard variant="outline" class="min-w-0" :ui="{ body: 'flex h-full flex-col gap-4 p-4 sm:p-5' }">
    <div class="flex items-center justify-between gap-2">
      <h2 class="text-sm font-semibold text-highlighted">{{ t('apiService.analytics.traffic') }}</h2>
      <UBadge v-if="analytics" icon="i-lucide-calendar" :label="`${d(at(analytics.from), { day: 'numeric', month: 'short' })} → ${d(at(analytics.to), { day: 'numeric', month: 'short' })}`" color="neutral" variant="outline" class="rounded-md" />
    </div>
    <div v-if="analytics" class="flex items-stretch gap-3">
      <span class="w-0.5 rounded-full bg-(--ui-border-accented)" aria-hidden="true" />
      <div class="flex flex-col gap-1">
        <div class="flex items-center gap-2">
          <span class="text-2xl leading-none font-semibold text-highlighted tabular-nums">{{ t('apiService.callsCount', { n: number(analytics.totals.calls) }, analytics.totals.calls) }}</span>
          <UBadge v-if="change != null" :label="`${change > 0 ? '+' : ''}${change}%`" :color="change >= 0 ? 'success' : 'error'" variant="subtle" size="sm" class="rounded-md tabular-nums" />
        </div>
        <span class="text-xs text-muted">{{ t('apiService.analytics.perDay', { n: number(perDay, { maximumFractionDigits: 0 }) }) }}</span>
      </div>
    </div>
    <div v-else class="flex flex-col gap-2"><USkeleton class="h-7 w-40" /><USkeleton class="h-3 w-32" /></div>
    <USkeleton v-if="!analytics" class="h-60 w-full" />
    <AppEmpty v-else-if="!analytics.totals.calls" size="sm" icon="i-lucide-arrow-left-right" :title="t('apiService.analytics.quiet')" :description="t('apiService.analytics.quietDesc')" />
    <ChartsFlow v-else v-model:active="active" :points="points" :height="230" :upper-label="t('apiService.kpi.calls')" :lower-label="t('apiService.analytics.worked')">
      <template #tooltip="{ index }">
        <p class="truncate text-xs text-muted">{{ d(at(analytics.daily[index]!.date), { weekday: 'long', day: 'numeric', month: 'long' }) }}</p>
        <p class="mt-1 text-xl leading-none font-semibold text-highlighted tabular-nums">{{ percent(analytics.daily[index]!.calls ? analytics.daily[index]!.errors / analytics.daily[index]!.calls : 0, 1) }}</p>
        <p class="text-[11px] text-muted">{{ t('apiService.kpi.errors') }}</p>
        <div class="mt-2.5 grid grid-cols-2 gap-2 border-t border-default pt-2.5">
          <div class="flex flex-col">
            <span class="flex items-center gap-1.5 text-[11px] text-muted"><span class="size-2 rounded-full bg-(--ui-text-muted)" />{{ t('apiService.kpi.calls') }}</span>
            <span class="text-sm font-semibold text-highlighted tabular-nums">{{ number(analytics.daily[index]!.calls) }}</span>
          </div>
          <div class="flex flex-col">
            <span class="flex items-center gap-1.5 text-[11px] text-muted"><span class="size-2 rounded-full bg-success" />{{ t('apiService.analytics.worked') }}</span>
            <span class="text-sm font-semibold text-highlighted tabular-nums">{{ number(analytics.daily[index]!.calls - analytics.daily[index]!.errors) }}</span>
          </div>
        </div>
      </template>
    </ChartsFlow>
    <div v-if="analytics?.totals.calls" class="mt-auto flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-muted">
      <span class="flex items-center gap-1.5"><span class="size-2 rounded-full bg-(--ui-text-muted)" />{{ t('apiService.kpi.calls') }}</span>
      <span class="flex items-center gap-1.5"><span class="size-2 rounded-full bg-success" />{{ t('apiService.analytics.worked') }}</span>
      <span class="flex items-center gap-1.5"><span class="h-2 w-3 rounded-sm bg-[repeating-linear-gradient(45deg,var(--ui-border-accented)_0_2px,transparent_2px_5px)]" />{{ t('apiService.analytics.failed') }}</span>
    </div>
  </UCard>
</template>

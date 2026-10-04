<!--
  Responses at a glance (F11, owner 2026-10-04: "a slim top, the table below"): one thin strip of
  four numbers. Responses in the period (change against the period before, tiny sparkline), to
  review (a slim meter; click filters the list), median time to fill in, completion (per form) or
  last response (inbox). Phones: two by two.
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
const newShare = computed(() => (props.insights.total ? props.insights.new / props.insights.total : 0))
</script>

<template>
  <div class="grid grid-cols-2 overflow-hidden rounded-lg border border-default bg-default lg:grid-cols-4" role="group" :aria-label="t('responses.kpi.label')">
    <!-- Responses in the period -->
    <div class="flex items-center justify-between gap-3 border-default px-4 py-3 max-lg:border-b lg:border-e">
      <div class="flex min-w-0 flex-col gap-0.5">
        <span class="truncate text-xs text-muted">{{ t('responses.kpi.period') }}</span>
        <div class="flex items-center gap-1.5">
          <span class="text-lg leading-tight font-semibold text-highlighted tabular-nums">{{ number(insights.period.count) }}</span>
          <UBadge v-if="trend !== null" :label="`${trend > 0 ? '+' : ''}${trend}%`" :color="trend >= 0 ? 'success' : 'error'" variant="subtle" size="xs" class="rounded tabular-nums" />
        </div>
        <span class="truncate text-[11px] text-dimmed">{{ t('responses.kpi.total', { n: number(insights.total) }) }}</span>
      </div>
      <ChartsSparkline :values="insights.daily.map(day => day.count)" :width="72" :height="26" class="hidden sm:block" />
    </div>

    <!-- To review -->
    <button
      type="button"
      class="group flex flex-col justify-center gap-1 border-default px-4 py-3 text-start transition-colors hover:bg-elevated/50 focus-visible:outline-2 focus-visible:-outline-offset-2 focus-visible:outline-(--ui-border-inverted) max-lg:border-b lg:border-e"
      :disabled="!insights.new"
      @click="emit('review')"
    >
      <span class="flex items-center justify-between gap-2 text-xs text-muted">
        {{ t('responses.kpi.toReview') }}
        <UIcon v-if="insights.new" name="i-lucide-arrow-right" class="size-3.5 opacity-0 transition-opacity group-hover:opacity-100 rtl:rotate-180" />
      </span>
      <span class="flex items-baseline gap-1.5">
        <span class="text-lg leading-tight font-semibold text-highlighted tabular-nums">{{ number(insights.new) }}</span>
        <span class="text-[11px] text-dimmed">{{ insights.total ? percent(newShare) : '' }}</span>
      </span>
      <span class="h-1 overflow-hidden rounded-full bg-elevated" role="presentation">
        <span class="block h-full rounded-full bg-info" :style="{ width: `${Math.min(100, newShare * 100)}%` }" />
      </span>
    </button>

    <!-- Time to fill in -->
    <div class="flex flex-col justify-center gap-0.5 border-default px-4 py-3 lg:border-e">
      <span class="truncate text-xs text-muted">{{ t('responses.kpi.time') }}</span>
      <span class="text-lg leading-tight font-semibold text-highlighted tabular-nums">{{ insights.median_seconds != null ? duration(Math.round(insights.median_seconds)) : '-' }}</span>
      <span class="truncate text-[11px] text-dimmed">{{ t('responses.kpi.timeHint') }}</span>
    </div>

    <!-- Completion (per form) or last response (inbox) -->
    <div v-if="perForm" class="flex flex-col justify-center gap-1 px-4 py-3">
      <span class="truncate text-xs text-muted">{{ t('responses.kpi.completion') }}</span>
      <span class="text-lg leading-tight font-semibold text-highlighted tabular-nums">{{ insights.completion_rate != null ? `${insights.completion_rate}%` : '-' }}</span>
      <span class="h-1 overflow-hidden rounded-full bg-elevated" role="presentation">
        <span class="block h-full rounded-full bg-inverted" :style="{ width: `${insights.completion_rate ?? 0}%` }" />
      </span>
    </div>
    <div v-else class="flex flex-col justify-center gap-0.5 px-4 py-3">
      <span class="truncate text-xs text-muted">{{ t('responses.kpi.last') }}</span>
      <span class="truncate text-lg leading-tight font-semibold text-highlighted">{{ insights.last_at ? relative(insights.last_at) : '-' }}</span>
      <span class="truncate text-[11px] text-dimmed">{{ insights.top_forms[0] ? t('responses.kpi.busiest', { name: insights.top_forms[0].name }) : t('responses.kpi.nothing') }}</span>
    </div>
  </div>
</template>

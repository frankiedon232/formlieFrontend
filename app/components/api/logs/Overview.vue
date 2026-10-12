<!--
  Top of API service → Request logs (locked list format, rule 21): two equal chart cards. Calls in
  the last 30 days (with the change, error share and answer time, daily bars), and calls by result
  (succeeded, refused by the caller's mistake, failed on our side) as thin lines whose legend filters.
-->
<script setup lang="ts">
import type { ApiLogInsights } from '#shared/types/apiService'

const props = defineProps<{ insights: ApiLogInsights | null; klass?: string | null }>()
const emit = defineEmits<{ klass: [value: string] }>()
const { t } = useI18n()
const { number, percent } = useFormat()
const trend = computed(() => (props.insights?.previous_30d ? Math.round(((props.insights.calls_30d - props.insights.previous_30d) / props.insights.previous_30d) * 100) : null))
const stats = computed(() =>
  props.insights
    ? [
        { label: t('apiService.kpi.errors'), value: percent(props.insights.calls_30d ? props.insights.errors_30d / props.insights.calls_30d : 0, 1) },
        { label: t('apiService.kpi.time'), value: props.insights.avg_ms == null ? '–' : t('dataSources.ms', { n: props.insights.avg_ms }) },
      ]
    : [],
)
const parts = computed(() => [
  { key: '2xx', label: t('apiService.logs.class.2xx'), count: props.insights?.by_class['2xx'] ?? 0, color: 'bg-green-500' },
  { key: '4xx', label: t('apiService.logs.class.4xx'), count: props.insights?.by_class['4xx'] ?? 0, color: 'bg-amber-500' },
  { key: '5xx', label: t('apiService.logs.class.5xx'), count: props.insights?.by_class['5xx'] ?? 0, color: 'bg-red-500' },
])
</script>

<template>
  <div class="grid shrink-0 gap-4 lg:grid-cols-2">
    <UCard variant="outline" :ui="{ body: 'flex h-full flex-col gap-4 p-4 sm:p-5' }">
      <div class="flex flex-col">
        <h2 class="text-sm font-semibold text-highlighted">{{ t('apiService.kpi.calls') }}</h2>
        <span class="text-xs text-muted">{{ t('forms.overview.last30Short') }}</span>
      </div>
      <div v-if="!insights" class="flex flex-1 items-end gap-5"><USkeleton class="h-16 w-48" /><USkeleton class="h-24 flex-1" /></div>
      <div v-else class="flex flex-1 items-end gap-5">
        <div class="flex shrink-0 flex-col gap-3">
          <div class="flex items-center gap-2.5">
            <UIcon name="i-lucide-scroll-text" class="size-5 text-muted" />
            <span class="text-3xl leading-none font-semibold text-highlighted tabular-nums">{{ number(insights.calls_30d) }}</span>
            <div class="flex flex-col gap-0.5">
              <UBadge v-if="trend !== null" :label="`${trend > 0 ? '+' : ''}${trend}%`" :color="trend >= 0 ? 'success' : 'error'" variant="subtle" size="sm" class="w-fit rounded-md tabular-nums" />
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
        <ChartsMiniBars :days="insights.daily" :label="t('apiService.kpi.calls')" />
      </div>
    </UCard>

    <UCard variant="outline" :ui="{ body: 'flex h-full flex-col gap-4 p-4 sm:p-5' }">
      <div class="flex items-start justify-between gap-2">
        <h2 class="text-sm font-semibold text-highlighted">{{ t('apiService.logs.byResult') }}</h2>
        <span class="text-xs text-muted">{{ t('forms.overview.last30Short') }}</span>
      </div>
      <div v-if="!insights" class="flex flex-1 items-end gap-6"><USkeleton class="h-24 flex-1" /></div>
      <div v-else class="flex flex-1 items-end gap-6">
        <ChartsLines :parts="parts" :selected="klass" class="min-w-0 flex-1" @pick="key => emit('klass', key)" />
        <ul class="hidden shrink-0 flex-col gap-1 sm:flex">
          <li v-for="part in parts" :key="part.key">
            <button
              type="button"
              class="flex w-full items-center gap-2 rounded-md px-1.5 py-0.5 text-start text-xs hover:bg-elevated focus-visible:outline-2 focus-visible:outline-(--ui-border-inverted)"
              :class="klass === part.key ? 'bg-elevated' : ''"
              :aria-pressed="klass === part.key"
              @click="emit('klass', part.key)"
            >
              <span class="size-2 shrink-0 rounded-[2px]" :class="part.color" />
              <span class="w-28 truncate text-default">{{ part.label }}</span>
              <span class="ms-auto font-medium text-highlighted tabular-nums">{{ number(part.count) }}</span>
            </button>
          </li>
        </ul>
      </div>
    </UCard>
  </div>
</template>

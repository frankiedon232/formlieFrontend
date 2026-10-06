<!--
  Top of API service → Services and Endpoints (locked list format, rule 21): two equal chart cards.
  Calls in the last 30 days (with the change, a few small stats and daily bars), and either the
  services by status or the endpoints by method as thin lines with a legend that filters the list.
-->
<script setup lang="ts">
import type { ApiInsights } from '#shared/types/apiService'
import { API_METHODS } from '#shared/utils/urls/public'

const props = defineProps<{ insights: ApiInsights | null; by: 'status' | 'method'; selected?: string | null; count: string }>()
const emit = defineEmits<{ pick: [key: string] }>()
const { t } = useI18n()
const { number, percent } = useFormat()

const trend = computed(() => (props.insights?.previous_30d ? Math.round(((props.insights.calls_30d - props.insights.previous_30d) / props.insights.previous_30d) * 100) : null))
const stats = computed(() => {
  const data = props.insights
  if (!data) return []
  return [
    { label: props.count, value: number(data.total) },
    { label: t('apiService.kpi.errors'), value: percent(data.calls_30d ? data.errors_30d / data.calls_30d : 0, 1), warn: data.calls_30d > 0 && data.errors_30d / data.calls_30d > 0.05 },
    { label: t('apiService.kpi.time'), value: data.avg_ms == null ? '–' : t('dataSources.ms', { n: data.avg_ms }) },
  ]
})
const METHOD_COLORS = { GET: 'bg-(--ui-text-highlighted)', POST: 'bg-green-500', PUT: 'bg-amber-500', DELETE: 'bg-red-500' } as const
const parts = computed(() =>
  props.by === 'status'
    ? [
        { key: 'active', label: t('status.active'), count: props.insights?.by_status.active ?? 0, color: 'bg-green-500' },
        { key: 'disabled', label: t('status.disabled'), count: props.insights?.by_status.disabled ?? 0, color: 'bg-(--ui-border-accented)' },
      ]
    : API_METHODS.map(method => ({ key: method, label: method, count: props.insights?.by_method[method] ?? 0, color: METHOD_COLORS[method] })),
)
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
            <UIcon name="i-lucide-arrow-left-right" class="size-5 text-muted" />
            <span class="text-3xl leading-none font-semibold text-highlighted tabular-nums">{{ number(insights.calls_30d) }}</span>
            <div class="flex flex-col gap-0.5">
              <UBadge v-if="trend !== null" :label="`${trend > 0 ? '+' : ''}${trend}%`" :color="trend >= 0 ? 'success' : 'error'" variant="subtle" size="sm" class="w-fit rounded-md tabular-nums" />
              <span class="text-[11px] text-muted">{{ t('responses.overview.vsBefore') }}</span>
            </div>
          </div>
          <dl class="flex gap-4">
            <div v-for="stat in stats" :key="stat.label" class="flex min-w-0 flex-col">
              <dt class="truncate text-[11px] text-muted">{{ stat.label }}</dt>
              <dd class="truncate text-sm font-medium tabular-nums" :class="stat.warn ? 'text-error' : 'text-highlighted'">{{ stat.value }}</dd>
            </div>
          </dl>
        </div>
        <ChartsMiniBars :days="insights.daily" :label="t('apiService.kpi.calls')" />
      </div>
    </UCard>

    <UCard variant="outline" :ui="{ body: 'flex h-full flex-col gap-4 p-4 sm:p-5' }">
      <div class="flex items-start justify-between gap-2">
        <h2 class="text-sm font-semibold text-highlighted">{{ by === 'status' ? t('apiService.kpi.byStatus') : t('apiService.kpi.byMethod') }}</h2>
        <span class="text-xs text-muted">{{ t('apiService.kpi.active', { n: number(insights?.by_status.active ?? 0) }) }}</span>
      </div>
      <div v-if="!insights" class="flex flex-1 items-end gap-6"><USkeleton class="h-24 flex-1" /></div>
      <AppEmpty v-else-if="!insights.total" size="xs" icon="i-lucide-route" :title="t('apiService.kpi.none')" />
      <div v-else class="flex flex-1 items-end gap-6">
        <ChartsLines :parts="parts" :selected="selected" class="min-w-0 flex-1" @pick="key => emit('pick', key)" />
        <ul class="hidden shrink-0 flex-col gap-1 sm:flex">
          <li v-for="part in parts" :key="part.key">
            <button
              type="button"
              class="flex w-full items-center gap-2 rounded-md px-1.5 py-0.5 text-start text-xs hover:bg-elevated focus-visible:outline-2 focus-visible:outline-(--ui-border-inverted)"
              :class="selected === part.key ? 'bg-elevated' : ''"
              :aria-pressed="selected === part.key"
              @click="emit('pick', part.key)"
            >
              <span class="size-2 shrink-0 rounded-[2px]" :class="part.color" />
              <span class="w-20 truncate text-default" :class="by === 'method' ? 'font-mono' : ''">{{ part.label }}</span>
              <span class="ms-auto font-medium text-highlighted tabular-nums">{{ number(part.count) }}</span>
            </button>
          </li>
        </ul>
      </div>
    </UCard>
  </div>
</template>

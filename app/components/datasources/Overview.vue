<!--
  Top of Data sources → Connections (locked list format, rule 21): two equal chart cards.
  Activity in the last 30 days (operations with their change, connections, read + write, average
  response time, missing permissions, daily bars) and connections by status as the design's thin
  lines with a legend that filters the list.
-->
<script setup lang="ts">
import { DATASOURCE_STATUSES, type DataSourceInsights } from '#shared/types/datasources'

const props = defineProps<{ insights: DataSourceInsights | null; status?: string | null }>()
const emit = defineEmits<{ status: [status: string] }>()
const { t } = useI18n()
const { number } = useFormat()

const trend = computed(() => (props.insights?.previous_30d ? Math.round(((props.insights.operations_30d - props.insights.previous_30d) / props.insights.previous_30d) * 100) : null))
const stats = computed(() => {
  const data = props.insights
  if (!data) return []
  return [
    { label: t('nav.dataConnections'), value: number(data.total) },
    { label: t('dataSources.formsUsing'), value: number(data.forms_sending) },
    { label: t('dataSources.kpi.latency'), value: data.avg_latency_ms === null ? '–' : t('dataSources.ms', { n: data.avg_latency_ms }) },
    { label: t('dataSources.kpi.missing'), value: number(data.missing_permissions) },
  ]
})
const parts = computed(() => DATASOURCE_STATUSES.map(key => ({ key, label: t(`status.${key}`), count: props.insights?.by_status[key] ?? 0, color: DATASOURCE_STATUS_META[key].fill })))
const needLook = computed(() => (props.insights ? props.insights.by_status.attention + props.insights.by_status.failing : 0))
</script>

<template>
  <div class="grid gap-4 lg:grid-cols-2">
    <UCard variant="outline" :ui="{ body: 'flex h-full flex-col gap-4 p-4 sm:p-5' }">
      <div class="flex flex-col">
        <h2 class="text-sm font-semibold text-highlighted">{{ t('dataSources.kpi.activity') }}</h2>
        <span class="text-xs text-muted">{{ t('forms.overview.last30Short') }}</span>
      </div>
      <div v-if="!insights" class="flex flex-1 items-end gap-5"><USkeleton class="h-16 w-48" /><USkeleton class="h-24 flex-1" /></div>
      <div v-else class="flex flex-1 items-end gap-5">
        <div class="flex shrink-0 flex-col gap-3">
          <div class="flex items-center gap-2.5">
            <UIcon name="i-lucide-database-zap" class="size-5 text-muted" />
            <span class="text-3xl leading-none font-semibold text-highlighted tabular-nums">{{ number(insights.operations_30d) }}</span>
            <div class="flex flex-col gap-0.5">
              <UBadge v-if="trend !== null" :label="`${trend > 0 ? '+' : ''}${trend}%`" :color="trend >= 0 ? 'success' : 'error'" variant="subtle" size="sm" class="w-fit rounded-md tabular-nums" />
              <span class="text-[11px] text-muted">{{ t('dataSources.kpi.operations') }}</span>
            </div>
          </div>
          <dl class="grid grid-cols-2 gap-x-5 gap-y-2 sm:flex sm:gap-4">
            <div v-for="stat in stats" :key="stat.label" class="flex min-w-0 flex-col">
              <dt class="truncate text-[11px] text-muted">{{ stat.label }}</dt>
              <dd class="truncate text-sm font-medium text-highlighted tabular-nums">{{ stat.value }}</dd>
            </div>
          </dl>
        </div>
        <ChartsMiniBars :days="insights.daily" :label="t('dataSources.kpi.operations')" />
      </div>
    </UCard>

    <UCard variant="outline" :ui="{ body: 'flex h-full flex-col gap-4 p-4 sm:p-5' }">
      <div class="flex items-start justify-between gap-2">
        <h2 class="text-sm font-semibold text-highlighted">{{ t('dataSources.kpi.byStatus') }}</h2>
        <span class="text-xs text-muted">{{ t('dataSources.kpi.needLook', { n: number(needLook) }) }}</span>
      </div>
      <div v-if="!insights" class="flex flex-1 items-end gap-6"><USkeleton class="h-24 flex-1" /></div>
      <div v-else class="flex flex-1 items-end gap-6">
        <ChartsLines :parts="parts" :selected="status" class="min-w-0 flex-1" @pick="key => emit('status', key)" />
        <ul class="hidden shrink-0 flex-col gap-1 sm:flex">
          <li v-for="part in parts" :key="part.key">
            <button
              type="button"
              class="flex w-full items-center gap-2 rounded-md px-1.5 py-0.5 text-start text-xs hover:bg-elevated focus-visible:outline-2 focus-visible:outline-(--ui-border-inverted)"
              :class="status === part.key ? 'bg-elevated' : ''"
              :aria-pressed="status === part.key"
              @click="emit('status', part.key)"
            >
              <span class="size-2 shrink-0 rounded-[2px]" :class="part.color" />
              <span class="w-24 truncate text-default">{{ part.label }}</span>
              <span class="ms-auto font-medium text-highlighted tabular-nums">{{ number(part.count) }}</span>
            </button>
          </li>
        </ul>
      </div>
    </UCard>
  </div>
</template>

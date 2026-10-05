<!--
  Top of Data sources → Activity (locked list format, rule 21): two equal chart cards. Everything
  that happened on the connections in the last 30 days (with the change, queries, changed rows,
  exports and failures, daily bars) and activity by kind as thin lines; the legend filters.
-->
<script setup lang="ts">
import { ACTIVITY_COLOR, ACTIVITY_KINDS, type ActivityInsights } from '#shared/utils/datasources/activity'

const props = defineProps<{ insights: ActivityInsights | null; kind?: string | null }>()
const emit = defineEmits<{ kind: [kind: string] }>()
const { t } = useI18n()
const { number } = useFormat()
const trend = computed(() => (props.insights?.previous_30d ? Math.round(((props.insights.total_30d - props.insights.previous_30d) / props.insights.previous_30d) * 100) : null))
const stats = computed(() =>
  props.insights
    ? [
        { label: t('dataActivity.kind.queries'), value: number(props.insights.by_kind.queries) },
        { label: t('dataActivity.kind.rows'), value: number(props.insights.by_kind.rows) },
        { label: t('dataActivity.kind.exports'), value: number(props.insights.by_kind.exports) },
        { label: t('dataActivity.failed'), value: number(props.insights.failed_30d), warn: props.insights.failed_30d > 0 },
      ]
    : [],
)
const parts = computed(() => ACTIVITY_KINDS.map(key => ({ key, label: t(`dataActivity.kind.${key}`), count: props.insights?.by_kind[key] ?? 0, color: ACTIVITY_COLOR[key] })))
</script>

<template>
  <div class="grid gap-4 lg:grid-cols-2">
    <UCard variant="outline" :ui="{ body: 'flex h-full flex-col gap-4 p-4 sm:p-5' }">
      <div class="flex flex-col">
        <h2 class="text-sm font-semibold text-highlighted">{{ t('dataActivity.kpi.title') }}</h2>
        <span class="text-xs text-muted">{{ t('forms.overview.last30Short') }}</span>
      </div>
      <div v-if="!insights" class="flex flex-1 items-end gap-5"><USkeleton class="h-16 w-48" /><USkeleton class="h-24 flex-1" /></div>
      <div v-else class="flex flex-1 items-end gap-5">
        <div class="flex shrink-0 flex-col gap-3">
          <div class="flex items-center gap-2.5">
            <UIcon name="i-lucide-activity" class="size-5 text-muted" />
            <span class="text-3xl leading-none font-semibold text-highlighted tabular-nums">{{ number(insights.total_30d) }}</span>
            <div class="flex flex-col gap-0.5">
              <UBadge v-if="trend !== null" :label="`${trend > 0 ? '+' : ''}${trend}%`" :color="trend >= 0 ? 'success' : 'error'" variant="subtle" size="sm" class="w-fit rounded-md tabular-nums" />
              <span class="text-[11px] text-muted">{{ t('responses.overview.vsBefore') }}</span>
            </div>
          </div>
          <dl class="grid grid-cols-2 gap-x-5 gap-y-2 sm:flex sm:gap-4">
            <div v-for="stat in stats" :key="stat.label" class="flex min-w-0 flex-col">
              <dt class="truncate text-[11px] text-muted">{{ stat.label }}</dt>
              <dd class="truncate text-sm font-medium tabular-nums" :class="stat.warn ? 'text-error' : 'text-highlighted'">{{ stat.value }}</dd>
            </div>
          </dl>
        </div>
        <ChartsMiniBars :days="insights.daily" :label="t('dataActivity.kpi.title')" />
      </div>
    </UCard>

    <UCard variant="outline" :ui="{ body: 'flex h-full flex-col gap-4 p-4 sm:p-5' }">
      <div class="flex items-start justify-between gap-2">
        <h2 class="text-sm font-semibold text-highlighted">{{ t('dataActivity.kpi.byKind') }}</h2>
        <span class="truncate text-xs text-muted">{{ insights?.by_connection[0] ? t('dataActivity.kpi.busiest', { name: insights.by_connection[0].name }) : '' }}</span>
      </div>
      <div v-if="!insights" class="flex flex-1 items-end gap-6"><USkeleton class="h-24 flex-1" /></div>
      <div v-else class="flex flex-1 items-end gap-6">
        <ChartsLines :parts="parts" :selected="kind" class="min-w-0 flex-1" @pick="key => emit('kind', key)" />
        <ul class="hidden shrink-0 flex-col gap-0.5 sm:flex">
          <li v-for="part in parts" :key="part.key">
            <button
              type="button"
              class="flex w-full items-center gap-2 rounded-md px-1.5 py-0.5 text-start text-xs hover:bg-elevated focus-visible:outline-2 focus-visible:outline-(--ui-border-inverted)"
              :class="kind === part.key ? 'bg-elevated' : ''"
              :aria-pressed="kind === part.key"
              @click="emit('kind', part.key)"
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

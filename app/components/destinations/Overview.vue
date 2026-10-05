<!--
  Top of Data sources → Destinations (locked list format, rule 21): two equal chart cards.
  Responses delivered in the last 30 days (with the change, forms storing in a database, pending,
  failed and held, daily bars) and forms by delivery status as thin lines; the legend filters.
-->
<script setup lang="ts">
import type { DestinationInsights, DestinationStatus } from '#shared/types/destinations'

const props = defineProps<{ insights: DestinationInsights | null; status?: string | null }>()
const emit = defineEmits<{ status: [status: string] }>()
const { t } = useI18n()
const { number } = useFormat()
const FILL: Record<DestinationStatus, string> = { active: 'bg-green-500', paused: 'bg-(--ui-text-dimmed)', failing: 'bg-red-500' }
const trend = computed(() => (props.insights?.previous_30d ? Math.round(((props.insights.sent_30d - props.insights.previous_30d) / props.insights.previous_30d) * 100) : null))
const stats = computed(() =>
  props.insights
    ? [
        { label: t('destinations.kpi.forms'), value: number(props.insights.total) },
        { label: t('destinations.kpi.pending'), value: number(props.insights.deliveries.pending) },
        { label: t('destinations.kpi.failed'), value: number(props.insights.deliveries.failed) },
        { label: t('destinations.kpi.held'), value: number(props.insights.deliveries.held) },
      ]
    : [],
)
const parts = computed(() => (['active', 'paused', 'failing'] as DestinationStatus[]).map(key => ({ key, label: t(`destinations.status.${key}`), count: props.insights?.by_status[key] ?? 0, color: FILL[key] })))
</script>

<template>
  <div class="grid gap-4 lg:grid-cols-2">
    <UCard variant="outline" :ui="{ body: 'flex h-full flex-col gap-4 p-4 sm:p-5' }">
      <div class="flex flex-col">
        <h2 class="text-sm font-semibold text-highlighted">{{ t('destinations.kpi.delivered') }}</h2>
        <span class="text-xs text-muted">{{ t('forms.overview.last30Short') }}</span>
      </div>
      <div v-if="!insights" class="flex flex-1 items-end gap-5"><USkeleton class="h-16 w-48" /><USkeleton class="h-24 flex-1" /></div>
      <div v-else class="flex flex-1 items-end gap-5">
        <div class="flex shrink-0 flex-col gap-3">
          <div class="flex items-center gap-2.5">
            <UIcon name="i-lucide-send" class="size-5 text-muted" />
            <span class="text-3xl leading-none font-semibold text-highlighted tabular-nums">{{ number(insights.sent_30d) }}</span>
            <div class="flex flex-col gap-0.5">
              <UBadge v-if="trend !== null" :label="`${trend > 0 ? '+' : ''}${trend}%`" :color="trend >= 0 ? 'success' : 'error'" variant="subtle" size="sm" class="w-fit rounded-md tabular-nums" />
              <span class="text-[11px] text-muted">{{ t('responses.overview.vsBefore') }}</span>
            </div>
          </div>
          <dl class="grid grid-cols-2 gap-x-5 gap-y-2 sm:flex sm:gap-4">
            <div v-for="stat in stats" :key="stat.label" class="flex min-w-0 flex-col">
              <dt class="truncate text-[11px] text-muted">{{ stat.label }}</dt>
              <dd class="truncate text-sm font-medium text-highlighted tabular-nums">{{ stat.value }}</dd>
            </div>
          </dl>
        </div>
        <ChartsMiniBars :days="insights.daily" :label="t('destinations.kpi.delivered')" />
      </div>
    </UCard>

    <UCard variant="outline" :ui="{ body: 'flex h-full flex-col gap-4 p-4 sm:p-5' }">
      <div class="flex items-start justify-between gap-2">
        <h2 class="text-sm font-semibold text-highlighted">{{ t('destinations.kpi.byStatus') }}</h2>
        <span class="text-xs text-muted">{{ t('destinations.kpi.failingCount', { n: number(insights?.by_status.failing ?? 0) }) }}</span>
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

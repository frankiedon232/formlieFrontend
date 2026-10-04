<!--
  The top of the Responses pages (F11, owner 2026-10-04: two cards with charts, in the design's
  style, docs/design 084447 / 092034). Responses: the period's count with its change, total,
  time to fill in and completion (or last response), and a compact bar chart of the period.
  Review status: thin lines grouped by status with shares and a legend; a status filters the list.
  Both cards share one height; phones stack them.
-->
<script setup lang="ts">
import { RESPONSE_STATUSES, type ResponseInsights, type ResponseStatus } from '#shared/types/responses'

const props = defineProps<{ insights: ResponseInsights; perForm?: boolean; status?: string | null }>()
const emit = defineEmits<{ status: [status: ResponseStatus]; insights: [] }>()
const { t, d } = useI18n()
const { number, relative } = useFormat()
const { duration } = useResponseFormat()

const trend = computed(() => {
  const { count, previous } = props.insights.period
  return previous ? Math.round(((count - previous) / previous) * 100) : null
})
const parts = computed(() => RESPONSE_STATUSES.map(key => ({ key, label: t(`status.${key}`), count: props.insights.status[key], color: RESPONSE_STATUS_META[key].fill })))
const daily = computed(() => props.insights.daily)
const top = computed(() => Math.max(1, ...daily.value.map(day => day.count)))
const active = ref<number | null>(null)
const dayLabel = (date: string) => d(new Date(`${date}T12:00:00`), { day: 'numeric', month: 'short' })
const stats = computed(() => [
  { label: t('responses.kpi.totalLabel'), value: number(props.insights.total) },
  { label: t('responses.kpi.time'), value: props.insights.median_seconds != null ? duration(Math.round(props.insights.median_seconds)) : '-' },
  props.perForm
    ? { label: t('responses.kpi.completion'), value: props.insights.completion_rate != null ? `${props.insights.completion_rate}%` : '-' }
    : { label: t('responses.kpi.last'), value: props.insights.last_at ? relative(props.insights.last_at) : '-' },
])
</script>

<template>
  <div class="grid gap-4 lg:grid-cols-2">
    <!-- Responses -->
    <UCard variant="outline" :ui="{ body: 'flex h-full flex-col gap-4 p-4 sm:p-5' }">
      <div class="flex items-start justify-between gap-2">
        <h2 class="text-sm font-semibold text-highlighted">{{ t('responses.overview.responses') }}</h2>
        <UButton icon="i-lucide-arrow-up-right" color="neutral" variant="outline" size="xs" square :aria-label="t('responses.tabs.summary')" @click="emit('insights')" />
      </div>
      <div class="flex flex-1 items-end gap-5">
        <div class="flex shrink-0 flex-col gap-3">
          <div class="flex items-center gap-2.5">
            <UIcon name="i-lucide-inbox" class="size-5 text-muted" />
            <span class="text-3xl leading-none font-semibold text-highlighted tabular-nums">{{ number(insights.period.count) }}</span>
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
        <!-- The period, day by day -->
        <div class="relative hidden h-24 min-w-0 flex-1 items-end gap-px sm:flex" role="img" :aria-label="t('responses.trend.title')">
          <span
            v-for="(day, index) in daily"
            :key="day.date"
            class="min-w-0 flex-1 rounded-t-[3px] bg-inverted transition-opacity"
            :class="active === null || active === index ? 'opacity-100' : 'opacity-35'"
            :style="{ height: `${(day.count / top) * 100}%`, minHeight: day.count ? '2px' : '0' }"
            @mouseenter="active = index"
            @mouseleave="active = null"
          />
          <span v-if="active !== null" class="pointer-events-none absolute -top-1 end-0 rounded-md border border-default bg-default px-2 py-0.5 text-[11px] whitespace-nowrap shadow-sm">
            {{ dayLabel(daily[active]!.date) }} · <span class="font-semibold text-highlighted tabular-nums">{{ number(daily[active]!.count) }}</span>
          </span>
        </div>
      </div>
    </UCard>

    <!-- Review status -->
    <UCard variant="outline" :ui="{ body: 'flex h-full flex-col gap-4 p-4 sm:p-5' }">
      <div class="flex items-start justify-between gap-2">
        <h2 class="text-sm font-semibold text-highlighted">{{ t('responses.breakdown.status') }}</h2>
        <span class="text-xs text-muted">{{ t('responses.overview.toReview', { n: number(insights.new) }) }}</span>
      </div>
      <div class="flex flex-1 items-end gap-6">
        <ChartsLines :parts="parts" :selected="status" class="min-w-0 flex-1" @pick="key => emit('status', key as ResponseStatus)" />
        <ul class="hidden shrink-0 flex-col gap-1.5 sm:flex">
          <li v-for="part in parts" :key="part.key">
            <button
              type="button"
              class="flex w-full items-center gap-2 rounded-md px-1.5 py-0.5 text-start text-xs hover:bg-elevated focus-visible:outline-2 focus-visible:outline-(--ui-border-inverted)"
              :class="status === part.key ? 'bg-elevated' : ''"
              :aria-pressed="status === part.key"
              @click="emit('status', part.key)"
            >
              <span class="size-2 shrink-0 rounded-[2px]" :class="part.color" />
              <span class="w-20 truncate text-default">{{ part.label }}</span>
              <span class="ms-auto font-medium text-highlighted tabular-nums">{{ number(part.count) }}</span>
            </button>
          </li>
        </ul>
      </div>
    </UCard>
  </div>
</template>

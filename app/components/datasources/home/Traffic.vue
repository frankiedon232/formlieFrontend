<!--
  Database traffic on the Data sources overview (the design's "Productivity Overview"): Formalie's
  operations on the connections in the last 30 days with their change, Daily / Weekly, and the flow
  chart of all operations vs responses delivered (the hatched gap is everything else: reads,
  checks, queries). Below, the activity by kind; each kind opens Activity filtered to it.
-->
<script setup lang="ts">
import type { DataSourceInsights } from '#shared/types/datasources'
import type { DestinationInsights } from '#shared/types/destinations'
import { ACTIVITY_COLOR, ACTIVITY_KINDS, type ActivityInsights } from '#shared/utils/datasources/activity'

const props = defineProps<{ sources: DataSourceInsights | null; deliveries: DestinationInsights | null; activity: ActivityInsights | null }>()
const { t, d } = useI18n()
const { number } = useFormat()

const step = ref<'day' | 'week'>('day')
const steps = computed(() => [
  { value: 'day', label: t('analytics.daily') },
  { value: 'week', label: t('analytics.weekly') },
])
const at = (date: string) => new Date(`${date}T12:00:00`)
const short = (date: string) => d(at(date), { day: 'numeric', month: 'short' })
const groups = computed(() => {
  const days = props.sources?.daily ?? []
  const sent = new Map((props.deliveries?.daily ?? []).map(day => [day.date, day.count]))
  const rows = days.map(day => ({ date: day.date, operations: day.count, delivered: Math.min(day.count, sent.get(day.date) ?? 0) }))
  if (step.value === 'day') return rows.map(row => ({ label: short(row.date), full: d(at(row.date), { weekday: 'long', day: 'numeric', month: 'long' }), ...row }))
  const out: { label: string; full: string; operations: number; delivered: number }[] = []
  rows.forEach((row, i) => {
    if (i % 7 === 0) out.push({ label: short(row.date), full: short(row.date), operations: 0, delivered: 0 })
    const group = out[out.length - 1]!
    group.operations += row.operations
    group.delivered += row.delivered
    group.full = `${group.label} → ${short(row.date)}`
  })
  return out
})
const points = computed(() => groups.value.map(group => ({ label: group.label, upper: group.operations, lower: group.delivered })))
const active = ref<number | null>(null)
watch(step, () => (active.value = null))
const change = computed(() => (props.sources?.previous_30d ? Math.round(((props.sources.operations_30d - props.sources.previous_30d) / props.sources.previous_30d) * 100) : null))
const kinds = computed(() => ACTIVITY_KINDS.map(kind => ({ kind, label: t(`dataActivity.kind.${kind}`), count: props.activity?.by_kind[kind] ?? 0, color: ACTIVITY_COLOR[kind] })))
</script>

<template>
  <UCard variant="outline" class="min-w-0" :ui="{ body: 'flex h-full flex-col gap-4 p-4 sm:p-5' }">
    <div class="flex items-center justify-between gap-2">
      <h2 class="text-sm font-semibold text-highlighted">{{ t('dataSources.home.traffic') }}</h2>
      <UBadge icon="i-lucide-calendar" :label="t('forms.overview.last30Short')" color="neutral" variant="outline" class="rounded-md" />
    </div>

    <div class="flex flex-wrap items-end justify-between gap-3">
      <div v-if="sources" class="flex items-stretch gap-3">
        <span class="w-0.5 rounded-full bg-(--ui-border-accented)" aria-hidden="true" />
        <div class="flex flex-col gap-1">
          <div class="flex items-center gap-2">
            <span class="text-2xl leading-none font-semibold text-highlighted tabular-nums">{{ t('dataSources.home.operations', { n: number(sources.operations_30d) }, sources.operations_30d) }}</span>
            <UBadge v-if="change != null" :label="`${change > 0 ? '+' : ''}${change}%`" :color="change >= 0 ? 'success' : 'error'" variant="subtle" size="sm" class="rounded-md tabular-nums" />
          </div>
          <span class="text-xs text-muted">{{ t('dataSources.home.delivered', { n: number(deliveries?.sent_30d ?? 0) }, deliveries?.sent_30d ?? 0) }}</span>
        </div>
      </div>
      <div v-else class="flex flex-col gap-2"><USkeleton class="h-7 w-44" /><USkeleton class="h-3 w-32" /></div>
      <UTabs v-model="step" :items="steps" :content="false" color="neutral" size="xs" :ui="SEGMENTED_UI" :aria-label="t('analytics.step')" />
    </div>

    <USkeleton v-if="!sources" class="h-60 w-full" />
    <AppEmpty v-else-if="!sources.operations_30d" size="sm" icon="i-lucide-activity" :title="t('dataSources.home.quiet')" :description="t('dataSources.home.quietDesc')" />
    <ChartsFlow v-else v-model:active="active" :points="points" :height="230" :upper-label="t('dataSources.home.allOperations')" :lower-label="t('dataSources.home.deliveredLabel')">
      <template #tooltip="{ index }">
        <p class="truncate text-xs text-muted">{{ groups[index]!.full }}</p>
        <p class="mt-1 text-xl leading-none font-semibold text-highlighted tabular-nums">{{ number(groups[index]!.operations) }}</p>
        <div class="mt-2.5 grid grid-cols-2 gap-2 border-t border-default pt-2.5">
          <div class="flex flex-col">
            <span class="flex items-center gap-1.5 text-[11px] text-muted"><span class="size-2 rounded-full bg-(--ui-text-muted)" />{{ t('dataSources.home.other') }}</span>
            <span class="text-sm font-semibold text-highlighted tabular-nums">{{ number(groups[index]!.operations - groups[index]!.delivered) }}</span>
          </div>
          <div class="flex flex-col">
            <span class="flex items-center gap-1.5 text-[11px] text-muted"><span class="size-2 rounded-full bg-success" />{{ t('dataSources.home.deliveredLabel') }}</span>
            <span class="text-sm font-semibold text-highlighted tabular-nums">{{ number(groups[index]!.delivered) }}</span>
          </div>
        </div>
      </template>
    </ChartsFlow>

    <div v-if="activity" class="mt-auto flex flex-wrap gap-1.5 pt-1">
      <UButton
        v-for="item in kinds"
        :key="item.kind"
        :to="{ path: '/data-sources/activity', query: { kind: item.kind } }"
        color="neutral"
        variant="outline"
        size="xs"
        class="rounded-full"
      >
        <span class="size-2 rounded-[2px]" :class="item.color" />
        <span>{{ item.label }}</span>
        <span class="font-semibold text-highlighted tabular-nums">{{ number(item.count) }}</span>
      </UButton>
    </div>
  </UCard>
</template>

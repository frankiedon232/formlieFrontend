<!--
  Conversion overview (F18, the design's "Productivity Overview"): completions in the period with
  their change and the daily average, Daily / Weekly / Monthly, and the flow chart of started vs
  completed (the hatched gap is people who left). The tooltip gives the completion rate of the
  chosen day, week or month with its change against the one before, and both counts.
-->
<script setup lang="ts">
import type { AnalyticsOverview } from '#shared/types/analytics'

const props = defineProps<{ overview: AnalyticsOverview | null; change: number | null }>()
const { t, d } = useI18n()
const { number } = useFormat()

const step = ref<'day' | 'week' | 'month'>('day')
const steps = computed(() => [
  { value: 'day', label: t('analytics.daily') },
  { value: 'week', label: t('analytics.weekly') },
  { value: 'month', label: t('analytics.monthly') },
])
const at = (date: string) => new Date(`${date}T12:00:00`)
const short = (date: string) => d(at(date), { day: 'numeric', month: 'short' })
const groups = computed(() => {
  const days = props.overview?.daily ?? []
  if (step.value === 'day') return days.map(day => ({ label: days.length > 14 ? short(day.date) : d(at(day.date), { weekday: 'long' }), full: d(at(day.date), { weekday: 'long', day: 'numeric', month: 'long' }), starts: day.starts, completions: day.completions }))
  // Weeks of 7 days from the start of the period; calendar months
  const out: { key: string; label: string; full: string; starts: number; completions: number }[] = []
  days.forEach((day, i) => {
    const key = step.value === 'week' ? String(Math.floor(i / 7)) : day.date.slice(0, 7)
    let group = out[out.length - 1]
    if (group?.key !== key) {
      const month = step.value === 'month'
      group = { key, label: month ? d(at(day.date), { month: 'short', year: '2-digit' }) : short(day.date), full: month ? d(at(day.date), { month: 'long', year: 'numeric' }) : short(day.date), starts: 0, completions: 0 }
      out.push(group)
    }
    group.starts += day.starts
    group.completions += day.completions
    if (step.value === 'week') group.full = `${group.label} → ${short(day.date)}`
  })
  return out
})
const points = computed(() => groups.value.map(group => ({ label: group.label, upper: group.starts, lower: group.completions })))
const active = ref<number | null>(null)
watch(step, () => (active.value = null))
const rate = (group?: { starts: number; completions: number }) => (group?.starts ? Math.round((group.completions / group.starts) * 1000) / 10 : 0)
const perDay = computed(() => (props.overview?.daily.length ? props.overview.totals.completions / props.overview.daily.length : 0))
const any = computed(() => !!props.overview?.daily.some(day => day.starts))
</script>

<template>
  <UCard variant="outline" class="min-w-0" :ui="{ body: 'flex h-full flex-col gap-4 p-4 sm:p-5' }">
    <div class="flex items-center justify-between gap-2">
      <h2 class="text-sm font-semibold text-highlighted">{{ t('analytics.conversion.title') }}</h2>
      <UBadge v-if="overview" icon="i-lucide-calendar" :label="`${d(at(overview.from), { day: 'numeric', month: 'short' })} → ${d(at(overview.to), { day: 'numeric', month: 'short', year: 'numeric' })}`" color="neutral" variant="outline" class="rounded-md" />
    </div>

    <div class="flex flex-wrap items-end justify-between gap-3">
      <div v-if="overview" class="flex items-stretch gap-3">
        <span class="w-0.5 rounded-full bg-(--ui-border-accented)" aria-hidden="true" />
        <div class="flex flex-col gap-1">
          <div class="flex items-center gap-2">
            <span class="text-2xl leading-none font-semibold text-highlighted tabular-nums">{{ t('analytics.conversion.completed', { n: number(overview.totals.completions) }, overview.totals.completions) }}</span>
            <UBadge v-if="change != null" :label="`${change > 0 ? '+' : ''}${change}%`" :color="change >= 0 ? 'success' : 'error'" variant="subtle" size="sm" class="rounded-md tabular-nums" />
          </div>
          <span class="text-xs text-muted">{{ t('analytics.conversion.perDay', { n: number(perDay, { maximumFractionDigits: 1 }) }) }}</span>
        </div>
      </div>
      <div v-else class="flex flex-col gap-2"><USkeleton class="h-7 w-40" /><USkeleton class="h-3 w-32" /></div>
      <UTabs v-model="step" :items="steps" :content="false" color="neutral" size="xs" :ui="SEGMENTED_UI" :aria-label="t('analytics.step')" />
    </div>

    <USkeleton v-if="!overview" class="h-64 w-full" />
    <AppEmpty v-else-if="!any" size="sm" icon="i-lucide-chart-spline" :title="t('analytics.conversion.empty')" :description="t('analytics.conversion.emptyDesc')" />
    <ChartsFlow v-else v-model:active="active" :points="points" :upper-label="t('analytics.started')" :lower-label="t('analytics.completedLabel')">
      <template #tooltip="{ index }">
        <div class="flex items-center gap-2">
          <span class="text-xl leading-none font-semibold text-highlighted tabular-nums">{{ number(rate(groups[index]), { maximumFractionDigits: 1 }) }}%</span>
          <UBadge
            v-if="index > 0 && groups[index - 1]!.starts"
            :label="`${rate(groups[index]) - rate(groups[index - 1]) >= 0 ? '+' : ''}${number(rate(groups[index]) - rate(groups[index - 1]), { maximumFractionDigits: 1 })}%`"
            :color="rate(groups[index]) >= rate(groups[index - 1]) ? 'success' : 'error'"
            variant="subtle"
            size="sm"
            class="rounded-md tabular-nums"
          />
        </div>
        <p class="mt-1 truncate text-xs text-muted">{{ t('analytics.rate') }} · {{ groups[index]!.full }}</p>
        <div class="mt-2.5 grid grid-cols-2 gap-2 border-t border-default pt-2.5">
          <div class="flex flex-col">
            <span class="flex items-center gap-1.5 text-[11px] text-muted"><span class="size-2 rounded-full bg-(--ui-text-muted)" />{{ t('analytics.started') }}</span>
            <span class="text-sm font-semibold text-highlighted tabular-nums">{{ number(groups[index]!.starts) }}</span>
          </div>
          <div class="flex flex-col">
            <span class="flex items-center gap-1.5 text-[11px] text-muted"><span class="size-2 rounded-full bg-success" />{{ t('analytics.completedLabel') }}</span>
            <span class="text-sm font-semibold text-highlighted tabular-nums">{{ number(groups[index]!.completions) }}</span>
          </div>
        </div>
      </template>
    </ChartsFlow>

    <div v-if="overview && any" class="mt-auto flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-muted">
      <span class="flex items-center gap-1.5"><span class="size-2 rounded-full bg-(--ui-text-muted)" />{{ t('analytics.started') }}</span>
      <span class="flex items-center gap-1.5"><span class="size-2 rounded-full bg-success" />{{ t('analytics.completedLabel') }}</span>
      <span class="flex items-center gap-1.5"><span class="h-2 w-3 rounded-sm bg-[repeating-linear-gradient(45deg,var(--ui-border-accented)_0_2px,transparent_2px_5px)]" />{{ t('analytics.conversion.left') }}</span>
    </div>
  </UCard>
</template>

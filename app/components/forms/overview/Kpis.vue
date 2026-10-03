<!--
  Form overview headline numbers, laid out like the design's KPI cards (docs/design 092034):
  title top-left with an ↗ link top-right; below, icon · big number · trend badge · caption.
  Responses trend = the last 15 days against the 15 before.
-->
<script setup lang="ts">
import type { FormOverview } from '#shared/types/forms'

const props = defineProps<{ formId: string; stats: FormOverview['stats']; daily: FormOverview['daily'] }>()
const { t } = useI18n()
const { number, relative } = useFormat()

const recent = computed(() => props.daily.reduce((sum, day) => sum + day.count, 0))
const trend = computed(() => {
  const half = Math.floor(props.daily.length / 2)
  const before = props.daily.slice(0, half).reduce((sum, day) => sum + day.count, 0)
  const after = props.daily.slice(half).reduce((sum, day) => sum + day.count, 0)
  return before ? Math.round(((after - before) / before) * 100) : null
})
const time = computed(() => {
  const s = props.stats.avg_seconds
  if (s == null) return '—'
  return s < 60 ? t('forms.overview.seconds', { n: s }) : t('forms.overview.minutesShort', { n: Math.round(s / 6) / 10 })
})

const cards = computed(() => [
  {
    key: 'responses',
    title: t('forms.overview.responses'),
    icon: 'i-lucide-inbox',
    value: number(props.stats.responses),
    trend: trend.value,
    caption: t('forms.overview.last30', { n: number(recent.value) }),
    to: `/responses?form=${props.formId}`,
  },
  {
    key: 'completion',
    title: t('forms.overview.completion'),
    icon: 'i-lucide-circle-check-big',
    value: `${props.stats.completion_rate}%`,
    trend: null,
    caption: t('forms.overview.funnel', { views: number(props.stats.views), starts: number(props.stats.starts) }),
    to: `/analytics?form=${props.formId}`,
  },
  {
    key: 'time',
    title: t('forms.overview.time'),
    icon: 'i-lucide-timer',
    value: time.value,
    trend: null,
    caption: t('forms.overview.timeHint'),
    to: `/analytics?form=${props.formId}`,
  },
  {
    key: 'last',
    title: t('forms.overview.lastResponse'),
    icon: 'i-lucide-clock-3',
    value: props.stats.last_response_at ? relative(props.stats.last_response_at) : '—',
    trend: null,
    caption: props.stats.last_response_at ? t('forms.overview.lastResponseHint') : t('forms.overview.noResponses'),
    to: `/responses?form=${props.formId}`,
  },
])
</script>

<template>
  <div class="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
    <UCard v-for="card in cards" :key="card.key" variant="outline" :ui="{ body: 'flex flex-col gap-4 p-4 sm:p-4' }">
      <div class="flex items-start justify-between gap-2">
        <h3 class="text-sm font-medium text-highlighted">{{ card.title }}</h3>
        <UButton :to="card.to" icon="i-lucide-arrow-up-right" color="neutral" variant="outline" size="xs" square :aria-label="card.title" />
      </div>
      <div class="flex min-w-0 items-center gap-2.5">
        <UIcon :name="card.icon" class="size-5 shrink-0 text-muted" />
        <span class="shrink-0 text-2xl leading-none font-semibold whitespace-nowrap text-highlighted tabular-nums">{{ card.value }}</span>
        <div class="flex min-w-0 flex-col gap-0.5">
          <UBadge
            v-if="card.trend !== null"
            :label="`${card.trend > 0 ? '+' : ''}${card.trend}%`"
            :color="card.trend >= 0 ? 'success' : 'error'"
            variant="subtle"
            size="sm"
            class="self-start tabular-nums"
          />
          <span class="truncate text-xs text-muted">{{ card.caption }}</span>
        </div>
      </div>
    </UCard>
  </div>
</template>

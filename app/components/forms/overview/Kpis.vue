<!-- Form overview headline numbers: responses, completion (with views → starts), median time, last response. -->
<script setup lang="ts">
import type { FormOverview } from '#shared/types/forms'

const props = defineProps<{ stats: FormOverview['stats']; recent: number }>()
const { t } = useI18n()
const { number, relative } = useFormat()

const minutes = computed(() => {
  const s = props.stats.avg_seconds
  if (s == null) return '—'
  return s < 60 ? t('forms.overview.seconds', { n: s }) : t('forms.overview.minutesShort', { n: Math.round(s / 6) / 10 })
})
</script>

<template>
  <div class="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
    <UCard variant="outline" :ui="{ body: 'p-4 sm:p-4' }">
      <p class="flex items-center gap-1.5 text-xs text-muted"><UIcon name="i-lucide-inbox" class="size-3.5" />{{ t('forms.overview.responses') }}</p>
      <p class="mt-1 text-2xl font-semibold text-highlighted tabular-nums">{{ number(stats.responses) }}</p>
      <p class="text-xs text-muted">{{ t('forms.overview.last30', { n: number(recent) }) }}</p>
    </UCard>
    <UCard variant="outline" :ui="{ body: 'p-4 sm:p-4' }">
      <p class="flex items-center gap-1.5 text-xs text-muted"><UIcon name="i-lucide-circle-check-big" class="size-3.5" />{{ t('forms.overview.completion') }}</p>
      <p class="mt-1 text-2xl font-semibold text-highlighted tabular-nums">{{ stats.completion_rate }}%</p>
      <UProgress :model-value="stats.completion_rate" color="neutral" size="xs" class="mt-1.5" :aria-label="t('forms.overview.completion')" />
      <p class="mt-1.5 text-xs text-muted">{{ t('forms.overview.funnel', { views: number(stats.views), starts: number(stats.starts) }) }}</p>
    </UCard>
    <UCard variant="outline" :ui="{ body: 'p-4 sm:p-4' }">
      <p class="flex items-center gap-1.5 text-xs text-muted"><UIcon name="i-lucide-timer" class="size-3.5" />{{ t('forms.overview.time') }}</p>
      <p class="mt-1 text-2xl font-semibold text-highlighted tabular-nums">{{ minutes }}</p>
      <p class="text-xs text-muted">{{ t('forms.overview.timeHint') }}</p>
    </UCard>
    <UCard variant="outline" :ui="{ body: 'p-4 sm:p-4' }">
      <p class="flex items-center gap-1.5 text-xs text-muted"><UIcon name="i-lucide-clock-3" class="size-3.5" />{{ t('forms.overview.lastResponse') }}</p>
      <p class="mt-1 text-2xl font-semibold text-highlighted">{{ stats.last_response_at ? relative(stats.last_response_at) : '—' }}</p>
      <p class="text-xs text-muted">{{ stats.last_response_at ? t('forms.overview.lastResponseHint') : t('forms.overview.noResponses') }}</p>
    </UCard>
  </div>
</template>

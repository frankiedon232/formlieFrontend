<!--
  A form's analytics as a card (locked card format, rule 21): a completion pill, status and ⋯ on
  top; the form name (red flag when fewer than 4 in 10 starters finish) and where most people stop;
  views, started, completed and time to fill in, in two columns; a divider, then the completion
  rate as a slim ink bar; the 30-day completions and their change at the bottom.
-->
<script setup lang="ts">
import type { DropdownMenuItem } from '@nuxt/ui'
import type { FormAnalyticsRow } from '#shared/types/analytics'

const props = defineProps<{ item: FormAnalyticsRow; actions: DropdownMenuItem[][] }>()
const { t } = useI18n()
const { number } = useFormat()
const { duration } = useResponseFormat()
const facts = computed(() => [
  { key: 'views', label: t('analytics.views'), value: number(props.item.views) },
  { key: 'starts', label: t('analytics.started'), value: number(props.item.starts) },
  { key: 'completions', label: t('analytics.completedLabel'), value: number(props.item.completions) },
  { key: 'time', label: t('analytics.time'), value: props.item.median_seconds ? duration(props.item.median_seconds) : '–' },
])
const flagged = computed(() => props.item.starts >= 10 && props.item.completion_rate < 40)
</script>

<template>
  <article class="group flex h-full flex-col rounded-lg border border-default bg-default p-4 transition-all hover:-translate-y-0.5 hover:border-accented hover:shadow-md focus-within:shadow-md">
    <div class="flex items-center justify-between gap-2">
      <span class="inline-flex min-w-0 items-center gap-1.5 rounded-md border border-default px-2 py-0.5 text-xs font-medium text-toned">
        <UIcon name="i-lucide-chart-spline" class="size-3.5 shrink-0 text-muted" />
        <span class="truncate">{{ t('analytics.card.rate', { n: number(item.completion_rate, { maximumFractionDigits: 1 }) }) }}</span>
      </span>
      <div class="flex shrink-0 items-center gap-1.5">
        <DataStatusBadge :status="item.status" />
        <UDropdownMenu :items="actions" :content="{ align: 'end' }">
          <UButton icon="i-lucide-ellipsis" color="neutral" variant="outline" size="xs" square :aria-label="t('dataView.actions')" />
        </UDropdownMenu>
      </div>
    </div>

    <div class="mt-3 flex min-w-0 flex-col">
      <div class="flex min-w-0 items-center gap-1.5">
        <UIcon v-if="flagged" name="i-lucide-flag" class="size-3.5 shrink-0 text-error" :aria-label="t('analytics.card.flag')" />
        <span class="truncate text-base font-semibold text-highlighted">{{ item.name }}</span>
      </div>
      <p class="truncate text-sm text-muted">{{ item.drop_off ? t('analytics.card.stop', { label: item.drop_off.field_label }) : t('analytics.card.noStop') }}</p>
    </div>

    <dl class="mt-3 grid grid-cols-2 gap-x-4 gap-y-2.5">
      <div v-for="fact in facts" :key="fact.key" class="flex min-w-0 flex-col gap-0.5">
        <dt class="truncate text-[11px] text-muted">{{ fact.label }}</dt>
        <dd class="h-5 truncate text-sm text-default tabular-nums">{{ fact.value }}</dd>
      </div>
    </dl>

    <div class="mt-auto pt-4">
      <div class="flex flex-col gap-1.5 border-t border-default pt-3">
        <div class="flex items-center justify-between text-xs">
          <span class="text-muted">{{ t('analytics.rate') }}</span>
          <span class="font-medium text-highlighted tabular-nums">{{ number(item.completion_rate, { maximumFractionDigits: 1 }) }}%</span>
        </div>
        <div class="h-1.5 overflow-hidden rounded-full bg-elevated"><div class="h-full rounded-full bg-inverted" :style="{ width: `${item.completion_rate}%` }" /></div>
      </div>
      <div class="mt-4 flex items-center justify-between gap-2">
        <span class="flex min-w-0 items-center gap-1.5 text-xs text-muted">
          <UIcon name="i-lucide-inbox" class="size-3.5 shrink-0" />
          <span class="truncate">{{ t('analytics.card.completions', { n: number(item.completions) }, item.completions) }}</span>
          <UBadge v-if="item.change != null" :label="`${item.change > 0 ? '+' : ''}${item.change}%`" :color="item.change >= 0 ? 'success' : 'error'" variant="subtle" size="xs" class="rounded-md tabular-nums" />
        </span>
        <ChartsSparkline :values="item.trend" :width="72" :height="20" />
      </div>
    </div>
  </article>
</template>

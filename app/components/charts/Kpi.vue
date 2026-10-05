<!--
  A KPI card in the design's style (docs/design 092034, "Active Projects"): the label with an
  outline ↗ button to where the number comes from, then an icon, the big number, its change as a
  small coloured badge and "from the previous period". `lowerIsBetter` turns the colours round
  (e.g. failures, time to fill in). Skeleton while `value` is null.
-->
<script setup lang="ts">
import type { RouteLocationRaw } from 'vue-router'

const props = defineProps<{ label: string; icon: string; value: string | null; change?: number | null; hint?: string; to?: RouteLocationRaw; lowerIsBetter?: boolean }>()
const { t } = useI18n()
const good = computed(() => props.change == null || props.change === 0 || (props.change > 0) !== !!props.lowerIsBetter)
</script>

<template>
  <div class="flex min-w-0 flex-col gap-3 rounded-lg border border-default bg-default p-3.5 sm:p-4">
    <div class="flex items-center justify-between gap-2">
      <h3 class="truncate text-sm font-semibold text-highlighted">{{ label }}</h3>
      <UButton v-if="to" :to="to" icon="i-lucide-arrow-up-right" color="neutral" variant="outline" size="xs" square class="shrink-0 rtl:-scale-x-100" :aria-label="t('analytics.open', { name: label })" />
    </div>
    <div v-if="value === null" class="flex items-center gap-2.5"><USkeleton class="size-5 rounded" /><USkeleton class="h-7 w-16" /><USkeleton class="h-4 w-20" /></div>
    <div v-else class="flex min-w-0 items-center gap-2.5">
      <UIcon :name="icon" class="size-5 shrink-0 text-muted" />
      <span class="leading-none font-semibold whitespace-nowrap text-highlighted tabular-nums" :class="value.length > 7 ? 'text-xl' : 'text-2xl'">{{ value }}</span>
      <div class="flex min-w-0 flex-col leading-tight">
        <UBadge v-if="change != null" :label="`${change > 0 ? '+' : ''}${change}%`" :color="good ? 'success' : 'error'" variant="subtle" size="sm" class="w-fit rounded-md tabular-nums" />
        <span class="text-[11px] whitespace-nowrap text-muted">{{ hint ?? t('analytics.fromPrevious') }}</span>
      </div>
    </div>
  </div>
</template>

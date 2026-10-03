<!--
  Responses per day, last 30 days (form overview). One series → one ink colour, no legend (the
  title names it); thin bars with 4px rounded tops on a recessive baseline, 2px gaps; hover or
  keyboard focus on a day shows its tooltip; a screen-reader table carries the same data.
-->
<script setup lang="ts">
const props = defineProps<{ days: { date: string; count: number }[] }>()
const { t, d } = useI18n()
const { number } = useFormat()

const max = computed(() => Math.max(1, ...props.days.map(day => day.count)))
const total = computed(() => props.days.reduce((sum, day) => sum + day.count, 0))
/** A rounded axis top (1, 2, 5 × 10ⁿ) so the guide line reads well. */
const top = computed(() => {
  const step = 10 ** Math.floor(Math.log10(max.value))
  return [1, 2, 5, 10].map(m => m * step).find(v => v >= max.value) ?? max.value
})
const active = ref<number | null>(null)
const label = (date: string) => d(new Date(`${date}T12:00:00Z`), { day: 'numeric', month: 'short' })
</script>

<template>
  <UCard variant="outline" :ui="{ body: 'p-4 sm:p-5' }">
    <div class="mb-4 flex flex-wrap items-end justify-between gap-2">
      <div>
        <h2 class="text-sm font-semibold text-highlighted">{{ t('forms.overview.trendTitle') }}</h2>
        <p class="text-xs text-muted">{{ t('forms.overview.trendDesc') }}</p>
      </div>
      <p class="text-2xl font-semibold text-highlighted tabular-nums">{{ number(total) }}</p>
    </div>

    <div v-if="total" class="relative">
      <!-- Guide: top value + baseline (recessive) -->
      <div class="pointer-events-none absolute inset-x-0 top-0 flex items-center gap-2" aria-hidden="true">
        <span class="text-[10px] text-dimmed tabular-nums">{{ number(top) }}</span>
        <span class="h-px flex-1 border-t border-dashed border-default" />
      </div>
      <div class="flex h-40 items-end gap-0.5 border-b border-default pt-5" role="img" :aria-label="t('forms.overview.trendAria', { total })">
        <button
          v-for="(day, index) in days"
          :key="day.date"
          type="button"
          class="group/bar relative flex h-full flex-1 items-end focus-visible:outline-none"
          :aria-label="`${label(day.date)}: ${t('forms.overview.responsesCount', { count: day.count }, day.count)}`"
          @mouseenter="active = index"
          @mouseleave="active = null"
          @focus="active = index"
          @blur="active = null"
        >
          <span
            class="w-full rounded-t-[4px] bg-inverted transition-opacity"
            :class="active === null || active === index ? 'opacity-100' : 'opacity-40'"
            :style="{ height: `${(day.count / top) * 100}%`, minHeight: day.count ? '2px' : '0' }"
          />
          <span
            v-if="active === index"
            class="absolute bottom-full left-1/2 z-10 mb-1 -translate-x-1/2 rounded-md border border-default bg-default px-2 py-1 text-xs whitespace-nowrap shadow-md"
          >
            <span class="block text-muted">{{ label(day.date) }}</span>
            <span class="font-semibold text-highlighted tabular-nums">{{ t('forms.overview.responsesCount', { count: day.count }, day.count) }}</span>
          </span>
        </button>
      </div>
      <div class="mt-1.5 flex justify-between text-[10px] text-dimmed" aria-hidden="true">
        <span>{{ label(days[0]!.date) }}</span>
        <span>{{ label(days[Math.floor(days.length / 2)]!.date) }}</span>
        <span>{{ label(days.at(-1)!.date) }}</span>
      </div>
      <table class="sr-only">
        <caption>{{ t('forms.overview.trendTitle') }}</caption>
        <tr v-for="day in days" :key="day.date">
          <th scope="row">{{ label(day.date) }}</th>
          <td>{{ day.count }}</td>
        </tr>
      </table>
    </div>
    <UEmpty
      v-else
      icon="i-lucide-chart-column"
      :title="t('forms.overview.noTrend')"
      :description="t('forms.overview.noTrendDesc')"
      variant="naked"
      size="sm"
    />
  </UCard>
</template>

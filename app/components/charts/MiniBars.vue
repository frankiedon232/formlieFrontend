<!--
  Compact column chart for the top cards (locked list-page format, owner 2026-10-04): thin bars
  with 3px rounded tops, no axes; hover shows the day and value in a small tag. Visual summary
  only (the card states the numbers), hidden below sm.
-->
<script setup lang="ts">
const props = withDefaults(defineProps<{ days: { date: string; count: number }[]; height?: string; label: string }>(), { height: 'h-24' })
const { d } = useI18n()
const { number } = useFormat()
const top = computed(() => Math.max(1, ...props.days.map(day => day.count)))
const active = ref<number | null>(null)
const dayLabel = (date: string) => d(new Date(`${date}T12:00:00`), { day: 'numeric', month: 'short' })
</script>

<template>
  <div class="relative hidden min-w-0 flex-1 items-end gap-px sm:flex" :class="height" role="img" :aria-label="label">
    <span
      v-for="(day, index) in days"
      :key="day.date"
      class="min-w-0 flex-1 rounded-t-[3px] bg-inverted transition-opacity"
      :class="active === null || active === index ? 'opacity-100' : 'opacity-35'"
      :style="{ height: `${(day.count / top) * 100}%`, minHeight: day.count ? '2px' : '0' }"
      @mouseenter="active = index"
      @mouseleave="active = null"
    />
    <span v-if="active !== null" class="pointer-events-none absolute -top-1 end-0 rounded-md border border-default bg-default px-2 py-0.5 text-[11px] whitespace-nowrap shadow-sm">
      {{ dayLabel(days[active]!.date) }} · <span class="font-semibold text-highlighted tabular-nums">{{ number(days[active]!.count) }}</span>
    </span>
  </div>
</template>

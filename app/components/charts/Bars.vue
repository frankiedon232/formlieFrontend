<!--
  Slim column chart (F11 insights; same look as the overview trend): one ink colour, thin bars with
  4px rounded tops and 2px gaps on a recessive baseline, a dashed guide at a round top value. Hover
  or keyboard focus shows the value; the others fade. A screen-reader list carries the same data.
-->
<script setup lang="ts">
const props = withDefaults(defineProps<{ points: { label: string; value: number; hint?: string }[]; height?: string; unit: (n: number) => string; axis?: number }>(), {
  height: 'h-44',
  axis: 3,
})
const { number } = useFormat()

const max = computed(() => Math.max(1, ...props.points.map(point => point.value)))
/** A round top (1, 2, 5 × 10ⁿ) so the guide reads well. */
const top = computed(() => {
  const step = 10 ** Math.floor(Math.log10(max.value))
  return [1, 2, 5, 10].map(m => m * step).find(v => v >= max.value) ?? max.value
})
const active = ref<number | null>(null)
/** A few labels under the axis (first, middle, last), never crowded. */
const ticks = computed(() => {
  const n = props.points.length
  if (n <= 1) return [0]
  return [...new Set(Array.from({ length: props.axis }, (_, i) => Math.round((i * (n - 1)) / (props.axis - 1))))]
})
</script>

<template>
  <div class="relative">
    <div class="pointer-events-none absolute inset-x-0 top-0 flex items-center gap-2" aria-hidden="true">
      <span class="text-[10px] text-dimmed tabular-nums">{{ number(top) }}</span>
      <span class="h-px flex-1 border-t border-dashed border-default" />
    </div>
    <div class="flex items-end gap-0.5 border-b border-default pt-5" :class="height" role="list">
      <button
        v-for="(point, index) in points"
        :key="index"
        type="button"
        role="listitem"
        class="group/bar relative flex h-full min-w-0 flex-1 items-end focus-visible:outline-none"
        :aria-label="`${point.label}: ${unit(point.value)}`"
        @mouseenter="active = index"
        @mouseleave="active = null"
        @focus="active = index"
        @blur="active = null"
      >
        <span
          class="w-full rounded-t-[4px] bg-inverted transition-opacity"
          :class="active === null || active === index ? 'opacity-100' : 'opacity-35'"
          :style="{ height: `${(point.value / top) * 100}%`, minHeight: point.value ? '2px' : '0' }"
        />
        <span
          v-if="active === index"
          class="absolute bottom-full z-10 mb-1 rounded-md border border-default bg-default px-2 py-1 text-xs whitespace-nowrap shadow-md"
          :class="index < points.length / 2 ? 'start-0' : 'end-0'"
        >
          <span class="block text-muted">{{ point.label }}</span>
          <span class="font-semibold text-highlighted tabular-nums">{{ unit(point.value) }}</span>
          <span v-if="point.hint" class="block text-[11px] text-dimmed">{{ point.hint }}</span>
        </span>
      </button>
    </div>
    <div class="relative mt-1.5 h-4 text-[11px] text-muted" aria-hidden="true">
      <span
        v-for="index in ticks"
        :key="index"
        class="absolute whitespace-nowrap"
        :class="index === 0 ? 'start-0' : index === points.length - 1 ? 'end-0' : '-translate-x-1/2 rtl:translate-x-1/2'"
        :style="index === 0 || index === points.length - 1 ? undefined : { insetInlineStart: `${((index + 0.5) / points.length) * 100}%` }"
      >
        {{ points[index]?.label }}
      </span>
    </div>
  </div>
</template>

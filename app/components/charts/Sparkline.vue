<!--
  Flat, slim trend line for KPI cards (F11): a 2px line with a faint fill under it, no axes. Purely
  visual (the card states the number); hidden from screen readers.
-->
<script setup lang="ts">
const props = withDefaults(defineProps<{ values: number[]; width?: number; height?: number }>(), { width: 96, height: 28 })

const path = computed(() => {
  const values = props.values.length > 1 ? props.values : [0, ...(props.values.length ? props.values : [0])]
  const max = Math.max(1, ...values)
  const step = props.width / (values.length - 1)
  const y = (v: number) => props.height - 2 - (v / max) * (props.height - 4)
  const line = values.map((v, i) => `${i ? 'L' : 'M'}${(i * step).toFixed(1)},${y(v).toFixed(1)}`).join(' ')
  return { line, area: `${line} L${props.width},${props.height} L0,${props.height} Z` }
})
</script>

<template>
  <svg :viewBox="`0 0 ${width} ${height}`" :width="width" :height="height" class="shrink-0 overflow-visible text-highlighted rtl:-scale-x-100" aria-hidden="true">
    <path :d="path.area" fill="currentColor" opacity="0.07" />
    <path :d="path.line" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" vector-effect="non-scaling-stroke" />
  </svg>
</template>

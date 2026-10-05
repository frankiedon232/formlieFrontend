<!--
  The design's overview chart (docs/design 092034, "Productivity Overview"): two thin lines with
  small markers (upper, e.g. started, and lower, e.g. completed), the gap between them hatched
  lightly, and the chosen column hatched in ink between the two lines with a dashed guide, a
  marker on each line and a tooltip card (slot `tooltip`). Hover, tap or arrow keys choose a
  column; the choice stays. Drawn in pixels (measured) so the hatching never stretches. A
  screen-reader list carries the same numbers.
-->
<script setup lang="ts">
interface FlowPoint {
  label: string
  upper: number
  lower: number
}
const props = withDefaults(defineProps<{ points: FlowPoint[]; height?: number; upperLabel: string; lowerLabel: string; format?: (n: number) => string }>(), { height: 260, format: undefined })
const active = defineModel<number | null>('active', { default: null })
const { t } = useI18n()
const { number } = useFormat()
const show = (n: number) => (props.format ? props.format(n) : number(n))

const box = useTemplateRef<HTMLElement>('box')
const { width } = useElementSize(box)
const uid = useId()
const TOP = 18
const BOTTOM = 10
const n = computed(() => Math.max(1, props.points.length))
const step = computed(() => (width.value || 1) / n.value)
const max = computed(() => Math.max(1, ...props.points.map(point => Math.max(point.upper, point.lower))) * 1.12)
const x = (i: number) => (i + 0.5) * step.value
const y = (v: number) => TOP + (1 - v / max.value) * (props.height - TOP - BOTTOM)
const line = (key: 'upper' | 'lower') => props.points.map((point, i) => `${i ? 'L' : 'M'}${x(i).toFixed(1)},${y(point[key]).toFixed(1)}`).join(' ')
const band = computed(() => {
  if (!props.points.length) return ''
  const top = props.points.map((point, i) => `${i ? 'L' : 'M'}${x(i).toFixed(1)},${y(point.upper).toFixed(1)}`).join(' ')
  const bottom = [...props.points].reverse().map((point, i) => `L${x(props.points.length - 1 - i).toFixed(1)},${y(point.lower).toFixed(1)}`).join(' ')
  return `${top} ${bottom} Z`
})
const markers = computed(() => props.points.length <= 45)

// The chosen column (sticky): the last one with something in it until the person picks another
const shown = computed(() => {
  if (active.value !== null && active.value < props.points.length) return active.value
  for (let i = props.points.length - 1; i >= 0; i--) if (props.points[i]!.lower) return i
  for (let i = props.points.length - 1; i >= 0; i--) if (props.points[i]!.upper) return i
  return props.points.length - 1
})
const point = computed(() => props.points[shown.value])
const column = computed(() => Math.max(6, Math.min(56, step.value * 0.62)))
function pick(event: PointerEvent) {
  const rect = box.value?.getBoundingClientRect()
  if (!rect) return
  const offset = document.dir === 'rtl' ? rect.right - event.clientX : event.clientX - rect.left
  active.value = Math.max(0, Math.min(props.points.length - 1, Math.floor(offset / step.value)))
}
function key(event: KeyboardEvent) {
  const forward = document.dir === 'rtl' ? 'ArrowLeft' : 'ArrowRight'
  const back = document.dir === 'rtl' ? 'ArrowRight' : 'ArrowLeft'
  const moves: Record<string, number> = { [forward]: 1, [back]: -1, Home: -Infinity, End: Infinity }
  if (!(event.key in moves)) return
  event.preventDefault()
  active.value = Math.max(0, Math.min(props.points.length - 1, shown.value + moves[event.key]!))
}
/** A handful of labels under the axis, never crowded; the chosen one always. */
const ticks = computed(() => {
  const count = Math.min(props.points.length, Math.max(2, Math.floor((width.value || 600) / 96)))
  const every = Math.max(1, Math.ceil(props.points.length / count))
  return props.points.map((_, i) => i).filter(i => i % every === 0 && Math.abs(i - shown.value) * step.value > 64)
})
const narrow = computed(() => !!width.value && width.value < 480)
const tooltipStart = computed(() => x(shown.value) + column.value / 2 + 12 + 210 < (width.value || 0))
</script>

<template>
  <div class="flex flex-col">
    <!-- Phones: the chosen column's card sits above the chart instead of over it -->
    <div v-if="point && narrow" class="mb-3 rounded-lg border border-default bg-default p-3" aria-live="polite">
      <slot name="tooltip" :point="point" :index="shown" />
    </div>
    <div
      ref="box"
      class="relative touch-pan-y outline-none focus-visible:ring-2 focus-visible:ring-(--ui-border-inverted) focus-visible:ring-offset-2 rounded-md"
      :style="{ height: `${height}px` }"
      tabindex="0"
      role="group"
      :aria-label="t('charts.flowHint')"
      @pointermove="pick"
      @pointerdown="pick"
      @keydown="key"
    >
      <svg v-if="width" :width="width" :height="height" class="absolute inset-0 overflow-visible rtl:-scale-x-100" aria-hidden="true">
        <defs>
          <pattern :id="`${uid}-soft`" width="12" height="12" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">
            <rect width="5" height="12" style="fill: var(--ui-border-accented)" opacity="0.55" />
          </pattern>
          <pattern :id="`${uid}-ink`" width="14" height="14" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">
            <rect width="14" height="14" style="fill: var(--ui-bg)" />
            <rect width="7" height="14" style="fill: var(--ui-bg-inverted)" />
          </pattern>
        </defs>
        <line :x1="0" :x2="width" :y1="height - BOTTOM" :y2="height - BOTTOM" style="stroke: var(--ui-border)" />
        <rect :x="x(shown) - column / 2 - 6" :width="column + 12" y="0" :height="height - BOTTOM" rx="4" style="fill: var(--ui-bg-elevated)" />
        <path :d="band" :fill="`url(#${uid}-soft)`" />
        <path :d="line('upper')" fill="none" style="stroke: var(--ui-border-accented)" stroke-width="1.5" stroke-linejoin="round" />
        <path :d="line('lower')" fill="none" style="stroke: var(--ui-border-accented)" stroke-width="1.5" stroke-linejoin="round" />
        <template v-if="markers">
          <template v-for="(item, i) in points" :key="i">
            <circle :cx="x(i)" :cy="y(item.upper)" r="2.5" style="fill: var(--ui-border-accented)" />
            <circle :cx="x(i)" :cy="y(item.lower)" r="2.5" style="fill: var(--ui-border-accented)" />
          </template>
        </template>
        <template v-if="point">
          <rect :x="x(shown) - column / 2" :width="column" :y="y(point.upper)" :height="Math.max(2, y(point.lower) - y(point.upper))" :fill="`url(#${uid}-ink)`" />
          <line :x1="x(shown)" :x2="x(shown)" y1="0" :y2="height - BOTTOM" style="stroke: var(--ui-text-highlighted)" stroke-dasharray="2 3" />
          <circle :cx="x(shown)" :cy="y(point.upper)" r="5" style="fill: var(--ui-text-muted); stroke: var(--ui-bg)" stroke-width="2.5" />
          <circle :cx="x(shown)" :cy="y(point.lower)" r="5" style="fill: var(--ui-success); stroke: var(--ui-bg)" stroke-width="2.5" />
        </template>
      </svg>
      <div
        v-if="point && width && !narrow"
        class="pointer-events-none absolute top-6 z-10 w-52 rounded-lg border border-default bg-default p-3 shadow-lg"
        :style="tooltipStart ? { insetInlineStart: `${x(shown) + column / 2 + 12}px` } : { insetInlineStart: `${Math.max(0, x(shown) - column / 2 - 12 - 208)}px` }"
        aria-live="polite"
      >
        <slot name="tooltip" :point="point" :index="shown">
          <p class="text-xs text-muted">{{ point.label }}</p>
        </slot>
      </div>
    </div>

    <div class="relative mt-2 h-5 text-[11px] text-muted" aria-hidden="true">
      <span v-for="i in ticks" :key="i" class="absolute -translate-x-1/2 whitespace-nowrap rtl:translate-x-1/2" :style="{ insetInlineStart: `${x(i)}px` }">{{ points[i]!.label }}</span>
      <span v-if="point" class="absolute -translate-x-1/2 whitespace-nowrap font-semibold text-highlighted rtl:translate-x-1/2" :style="{ insetInlineStart: `${x(shown)}px` }">
        <UIcon name="i-lucide-triangle" class="absolute -top-2.5 start-1/2 size-2 -translate-x-1/2 fill-current rtl:translate-x-1/2" />{{ point.label }}
      </span>
    </div>

    <ul class="sr-only">
      <li v-for="(item, i) in points" :key="i">{{ item.label }}: {{ upperLabel }} {{ show(item.upper) }}, {{ lowerLabel }} {{ show(item.lower) }}</li>
    </ul>
  </div>
</template>

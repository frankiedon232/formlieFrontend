<!--
  A row of chips that may not fit (owner 2026-10-04): a rounded track with a subtle border and a
  solid light background, no scrollbar. Edge fades in the track's own colour (so they match it,
  not the page) show only where more chips are hidden; the mouse wheel moves the row sideways; small,
  almost hidden arrows at the ends move it too; a clicked chip (`data-chip`) glides to the centre.
  Works right to left. Chips are the slot; style them as segments (active = raised).
-->
<script setup lang="ts">
defineProps<{ label: string }>()
const { t } = useI18n()
const track = useTemplateRef<HTMLElement>('track')
const canStart = ref(false)
const canEnd = ref(false)
const rtl = () => !!track.value && getComputedStyle(track.value).direction === 'rtl'

function update() {
  const el = track.value
  if (!el) return
  const max = el.scrollWidth - el.clientWidth
  const at = Math.abs(el.scrollLeft)
  canStart.value = at > 2
  canEnd.value = at < max - 2
}
useResizeObserver(track, update)
onMounted(update)

/** A vertical wheel moves the row sideways (only when it can move). */
function onWheel(event: WheelEvent) {
  const el = track.value
  if (!el || el.scrollWidth <= el.clientWidth || Math.abs(event.deltaY) <= Math.abs(event.deltaX)) return
  event.preventDefault()
  el.scrollBy({ left: event.deltaY * (rtl() ? -1 : 1) })
}
/** Arrows: most of a view towards the start or the end. */
function nudge(towards: 'start' | 'end') {
  const el = track.value
  if (!el) return
  const step = el.clientWidth * 0.6 * (towards === 'end' ? 1 : -1)
  el.scrollBy({ left: rtl() ? -step : step, behavior: 'smooth' })
}
/**
 * A clicked chip glides to the centre: measured after the page reacts to the click (a re-render
 * would cancel the browser's own smooth scroll), and in screen terms, so right to left works too.
 */
async function center(event: MouseEvent) {
  const chip = (event.target as HTMLElement).closest<HTMLElement>('[data-chip]')
  const el = track.value
  if (!chip || !el) return
  await nextTick()
  const box = el.getBoundingClientRect()
  const item = chip.getBoundingClientRect()
  el.scrollBy({ left: item.left + item.width / 2 - (box.left + box.width / 2), behavior: 'smooth' })
}
</script>

<template>
  <div class="relative rounded-full border border-default bg-elevated p-1" role="group" :aria-label="label">
    <div
      ref="track"
      class="flex gap-1 overflow-x-auto scroll-smooth [scrollbar-width:none] [&::-webkit-scrollbar]:hidden"
      @scroll.passive="update"
      @wheel="onWheel"
      @click="center"
    >
      <slot />
    </div>

    <!-- Fades in the track's own colour, and the almost hidden arrows -->
    <div
      class="pointer-events-none absolute inset-y-0 start-0 w-14 rounded-s-full bg-linear-to-r from-(--ui-bg-elevated) from-40% to-transparent transition-opacity rtl:bg-linear-to-l"
      :class="canStart ? 'opacity-100' : 'opacity-0'"
      aria-hidden="true"
    />
    <div
      class="pointer-events-none absolute inset-y-0 end-0 w-14 rounded-e-full bg-linear-to-l from-(--ui-bg-elevated) from-40% to-transparent transition-opacity rtl:bg-linear-to-r"
      :class="canEnd ? 'opacity-100' : 'opacity-0'"
      aria-hidden="true"
    />
    <UButton
      v-show="canStart"
      icon="i-lucide-chevron-left"
      color="neutral"
      variant="ghost"
      size="xs"
      square
      class="absolute start-1 top-1/2 -translate-y-1/2 rounded-full opacity-50 hover:bg-default hover:opacity-100 focus-visible:opacity-100 rtl:rotate-180"
      :aria-label="t('app.scroller.back')"
      @click="nudge('start')"
    />
    <UButton
      v-show="canEnd"
      icon="i-lucide-chevron-right"
      color="neutral"
      variant="ghost"
      size="xs"
      square
      class="absolute end-1 top-1/2 -translate-y-1/2 rounded-full opacity-50 hover:bg-default hover:opacity-100 focus-visible:opacity-100 rtl:rotate-180"
      :aria-label="t('app.scroller.more')"
      @click="nudge('end')"
    />
  </div>
</template>

import type { MaybeElementRef } from '@vueuse/core'

/**
 * The beat of an animated product demo (owner, 2026-10-13: "animated demos, so it does not look like all images").
 * `step` counts 0 … total, one beat every `every` ms, holds the full picture for `hold` beats, then starts again.
 * Prerendered, for reduced motion and before the page is idle, it sits on the full picture (step = total).
 */
export function useDemoLoop(target: MaybeElementRef, total: number, every = 1100, hold = 3) {
  const { live, paused } = useSectionMotion(target)
  const tick = ref(total + hold)

  useIntervalFn(() => {
    if (!live.value || paused.value) return
    tick.value = (tick.value + 1) % (total + hold + 1)
  }, every)

  // Restart from the beginning when motion starts, so the story plays from its first beat.
  watch(live, value => {
    if (value) tick.value = 0
  })

  const step = computed(() => (live.value ? Math.min(tick.value, total) : total))
  return { step, live, paused }
}

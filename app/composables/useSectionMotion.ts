import type { MaybeElementRef } from '@vueuse/core'

/**
 * Motion rules for the site's animations (CLAUDE.md rule 8, docs/DESIGN.md):
 * - `still`: the visitor asked for less motion, so nothing moves (SMIL dots are not drawn, CSS uses motion-safe:).
 * - `paused`: the section is off screen; CSS animations pause through `.motion-paused` and SVG (SMIL)
 *   animations through pauseAnimations(), so nothing runs where nobody looks.
 * On the server both are false, so the prerendered page shows the full picture.
 */
export function useSectionMotion(target: MaybeElementRef) {
  const still = useMediaQuery('(prefers-reduced-motion: reduce)')
  const visible = ref(true)

  useIntersectionObserver(
    target,
    ([entry]) => {
      visible.value = entry?.isIntersecting ?? true
    },
    { rootMargin: '120px' },
  )

  const paused = computed(() => !visible.value)

  watch(paused, value => {
    const root = unrefElement(target) as HTMLElement | undefined
    root?.querySelectorAll('svg').forEach(svg => (value ? svg.pauseAnimations() : svg.unpauseAnimations()))
  })

  return { still, paused }
}

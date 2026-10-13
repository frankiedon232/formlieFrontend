import type { MaybeElementRef } from '@vueuse/core'

/**
 * Motion rules for the site's animations (CLAUDE.md rule 8, docs/DESIGN.md):
 * - `still`: the visitor asked for less motion, so nothing moves (SMIL dots are not drawn, CSS uses motion-safe:).
 * - `ready`: motion starts only once the page is idle after loading, so a slow phone paints and becomes usable
 *   first (S7 performance pass); until then everything stands still, exactly as prerendered.
 * - `paused`: not ready yet, or the section is off screen; CSS animations pause through `.motion-paused` and SVG
 *   (SMIL) animations through pauseAnimations(), so nothing runs where nobody looks.
 * - `live`: SMIL points of light may be drawn (ready and not still).
 */
export function useSectionMotion(target: MaybeElementRef) {
  const still = useMediaQuery('(prefers-reduced-motion: reduce)')
  const visible = ref(true)
  const ready = useState('motion-ready', () => false)

  onMounted(() => {
    if (ready.value) return
    const start = () => (ready.value = true)
    if ('requestIdleCallback' in window) window.requestIdleCallback(start, { timeout: 2500 })
    else setTimeout(start, 1200)
  })

  useIntersectionObserver(
    target,
    ([entry]) => {
      visible.value = entry?.isIntersecting ?? true
    },
    { rootMargin: '120px' },
  )

  const paused = computed(() => !ready.value || !visible.value)
  const live = computed(() => ready.value && !still.value)

  watch(paused, value => {
    const root = unrefElement(target) as HTMLElement | undefined
    root?.querySelectorAll('svg').forEach(svg => (value ? svg.pauseAnimations() : svg.unpauseAnimations()))
  })

  return { still, paused, live, ready }
}

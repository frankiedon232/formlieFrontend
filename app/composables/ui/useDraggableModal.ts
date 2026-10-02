const KEY_STEP = 16
const KEY_STEP_LARGE = 64

/**
 * Lets a modal be moved by its header (CLAUDE.md rule 1) with mouse, touch or keyboard.
 * `handle` is any element inside the modal header; the whole header becomes the drag area.
 * Offsets with margin-left/top: Nuxt UI centres the modal with the `translate` property and
 * animates it with `transform`, so margins move it without fighting either (and work in RTL).
 * Disabled below `sm` — on phones modals stay docked.
 */
export function useDraggableModal() {
  const handle = ref<HTMLElement | null>(null)
  const offset = reactive({ x: 0, y: 0 })
  const dragging = ref(false)
  const enabled = useMediaQuery('(min-width: 640px)')

  const dialog = computed(() => handle.value?.closest<HTMLElement>('[role="dialog"]') ?? null)
  const header = computed(() => handle.value?.closest<HTMLElement>('[data-slot="header"]') ?? null)

  let start = { pointerX: 0, pointerY: 0, x: 0, y: 0 }

  function apply() {
    const el = dialog.value
    if (!el) return
    if (!enabled.value) {
      el.style.marginLeft = ''
      el.style.marginTop = ''
      return
    }
    // Keep at least 48px of the dialog on screen.
    const rect = el.getBoundingClientRect()
    const maxX = window.innerWidth / 2 + rect.width / 2 - 48
    const maxY = window.innerHeight / 2 + rect.height / 2 - 48
    offset.x = Math.max(-maxX, Math.min(maxX, offset.x))
    offset.y = Math.max(-maxY, Math.min(maxY, offset.y))
    el.style.marginLeft = `${offset.x}px`
    el.style.marginTop = `${offset.y}px`
  }

  function reset() {
    offset.x = 0
    offset.y = 0
    apply()
  }

  useEventListener(header, 'pointerdown', (event: PointerEvent) => {
    if (!enabled.value || event.button !== 0) return
    // Buttons and links inside the header keep working; the grip button itself drags.
    const target = event.target as HTMLElement
    if (target.closest('a, input, button:not([data-drag-handle])')) return
    dragging.value = true
    start = { pointerX: event.clientX, pointerY: event.clientY, x: offset.x, y: offset.y }
    header.value?.setPointerCapture(event.pointerId)
  })

  useEventListener(header, 'pointermove', (event: PointerEvent) => {
    if (!dragging.value) return
    offset.x = start.x + event.clientX - start.pointerX
    offset.y = start.y + event.clientY - start.pointerY
    apply()
  })

  const stop = (event: PointerEvent) => {
    dragging.value = false
    if (header.value?.hasPointerCapture(event.pointerId)) header.value.releasePointerCapture(event.pointerId)
  }
  useEventListener(header, 'pointerup', stop)
  useEventListener(header, 'pointercancel', stop)

  watchEffect(() => {
    const el = header.value
    if (!el) return
    el.style.cursor = enabled.value ? (dragging.value ? 'grabbing' : 'grab') : ''
    el.style.userSelect = enabled.value ? 'none' : ''
  })

  /** Keyboard alternative (rule 7): arrows move, Shift = bigger steps, Home re-centres. */
  function onKeydown(event: KeyboardEvent) {
    if (!enabled.value) return
    if (event.key === 'Home') {
      event.preventDefault()
      reset()
      return
    }
    const step = event.shiftKey ? KEY_STEP_LARGE : KEY_STEP
    const moves: Record<string, [number, number]> = {
      ArrowLeft: [-step, 0],
      ArrowRight: [step, 0],
      ArrowUp: [0, -step],
      ArrowDown: [0, step],
    }
    const move = moves[event.key]
    if (!move) return
    event.preventDefault()
    offset.x += move[0]
    offset.y += move[1]
    apply()
  }

  watch(enabled, apply)

  return { handle, enabled, reset, onKeydown }
}

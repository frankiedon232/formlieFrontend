/**
 * Hover/focus "peek" of the menu column while the sidebar is collapsed (FRONTEND-SPEC §2).
 * Shared between the sidebar rail and the peek overlay, which are siblings in the layout.
 * `mode` = how it opened: keyboard focus makes the sidebar inert (clean Tab order),
 * hover leaves the rail clickable.
 */
const PEEK_DELAY_MS = 150
export const SIDEBAR_ELEMENT_ID = 'dashboard-sidebar-main'
export const RAIL_NAV_ID = 'sidebar-rail-nav'

let timer: ReturnType<typeof setTimeout> | undefined

export function useSidebarPeek() {
  const open = useState('app:sidebar-peek', () => false)
  const mode = useState<'hover' | 'focus'>('app:sidebar-peek-mode', () => 'hover')
  const collapsed = useState('app:sidebar-collapsed', () => false)
  const isDesktop = useMediaQuery('(min-width: 1024px)')

  const available = computed(() => collapsed.value && isDesktop.value)

  function schedule(value: boolean) {
    clearTimeout(timer)
    if (!available.value) return
    timer = setTimeout(() => {
      if (value && !open.value) mode.value = 'hover'
      open.value = value
    }, PEEK_DELAY_MS)
  }

  function close() {
    clearTimeout(timer)
    open.value = false
  }

  return { open, mode, collapsed, available, schedule, close }
}

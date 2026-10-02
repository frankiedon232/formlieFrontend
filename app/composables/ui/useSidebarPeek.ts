/**
 * Hover/focus "peek" of the full menu while the sidebar is collapsed (FRONTEND-SPEC §2).
 * Shared between the sidebar (rail) and the peek overlay, which are siblings in the layout.
 */
const PEEK_DELAY_MS = 150
export const SIDEBAR_ELEMENT_ID = 'dashboard-sidebar-main'

let timer: ReturnType<typeof setTimeout> | undefined

export function useSidebarPeek() {
  const open = useState('app:sidebar-peek', () => false)
  const collapsed = useState('app:sidebar-collapsed', () => false)
  const isDesktop = useMediaQuery('(min-width: 1024px)')

  const available = computed(() => collapsed.value && isDesktop.value)

  function schedule(value: boolean) {
    clearTimeout(timer)
    if (!available.value) return
    timer = setTimeout(() => {
      open.value = value
    }, PEEK_DELAY_MS)
  }

  function close() {
    clearTimeout(timer)
    open.value = false
  }

  return { open, collapsed, available, schedule, close }
}

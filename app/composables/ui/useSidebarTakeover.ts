/**
 * A page can take over the sidebar's menu column (F12 M3, owner 2026-10-05): the Database
 * explorer puts its connection and table tree there, so the page itself keeps the full width for
 * the data. The rail stays. An arrow at the top goes back to the menu; from the menu, a button
 * returns to the page's panel. Only on desktop with the sidebar expanded; elsewhere the page
 * opens the same content in a panel from the side.
 */
export const SIDEBAR_TAKEOVER_ID = 'sidebar-takeover'

export function useSidebarTakeover() {
  /** The page that owns the column: its title and icon (null when no page uses it). */
  const owner = useState<{ title: string; icon: string } | null>('app:sidebar-takeover', () => null)
  /** The person went back to the menu. */
  const dismissed = useState('app:sidebar-takeover-dismissed', () => false)
  const { collapsed } = useSidebarPeek()
  const isDesktop = useMediaQuery('(min-width: 1024px)')

  /** The page's content is in the menu column right now. */
  const shown = computed(() => !!owner.value && !dismissed.value && !collapsed.value && isDesktop.value)

  /** Called by the page: takes the column while it is mounted. */
  function claim(title: MaybeRefOrGetter<string>, icon: string) {
    onMounted(() => {
      dismissed.value = false
      watchEffect(() => (owner.value = { title: toValue(title), icon }))
    })
    onBeforeUnmount(() => {
      owner.value = null
      dismissed.value = false
    })
  }

  return { owner, dismissed, shown, claim }
}

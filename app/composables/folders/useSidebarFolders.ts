/**
 * Which folders the sidebar shows (owner 2026-10-05: folders must not take over the menu as they
 * grow). Per person, in this browser like the table / grid choice: pinned folders first (up to 5),
 * then the ones opened most recently, then the busiest, never more than 5 rows; the FOLDERS group
 * can be folded away. Nothing here is secret (folder ids only).
 */
export const SIDEBAR_FOLDERS = 5

export function useSidebarFolders() {
  const pinned = useLocalStorage<string[]>('formalie:folders:pinned', [])
  const recent = useLocalStorage<string[]>('formalie:folders:recent', [])
  const open = useLocalStorage<boolean>('formalie:sidebar:folders-open', true)

  const isPinned = (id: string) => pinned.value.includes(id)
  const canPin = computed(() => pinned.value.length < SIDEBAR_FOLDERS)
  function togglePin(id: string) {
    pinned.value = isPinned(id) ? pinned.value.filter(item => item !== id) : canPin.value ? [...pinned.value, id] : pinned.value
  }
  /** A folder was opened or created: it moves to the front of the recent list. */
  function visit(id: string) {
    recent.value = [id, ...recent.value.filter(item => item !== id)].slice(0, 20)
  }
  /** The folders to show, from all of them (shared rule, see pickSidebarFolders). */
  const pick = <T extends { id: string; count: number }>(folders: T[]) => pickSidebarFolders(folders, pinned.value, recent.value, SIDEBAR_FOLDERS)

  return { pinned, recent, open, isPinned, canPin, togglePin, visit, pick }
}
